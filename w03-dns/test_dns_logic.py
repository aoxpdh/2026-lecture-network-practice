import unittest
from task1_resolve import Resolver, ROOT_SERVERS
from dns_transport import parse_response


def rr(name, kind, value):
    return {"name": name, "type": kind, "value": value, "ttl": 60}


def response(answer=(), authority=(), additional=(), aa=False):
    return {"status": "NOERROR", "aa": aa, "answer": list(answer),
            "authority": list(authority), "additional": list(additional)}


class ResolverTests(unittest.TestCase):
    def make_resolver(self, records, **kwargs):
        def transport(name, server, recursive):
            self.assertFalse(recursive)
            result = records.get((name, server), RuntimeError("timeout"))
            if isinstance(result, Exception):
                raise result
            return result
        return Resolver(transport=transport, **kwargs)

    def test_missing_glue_and_server_fallback(self):
        root = ROOT_SERVERS[0]
        r = self.make_resolver({
            ("www.example.test", root): response(authority=[
                rr("example.test", "NS", "ns.other.test")]),
            ("ns.other.test", root): response(
                answer=[rr("ns.other.test", "A", "192.0.2.1")], aa=True),
            ("www.example.test", "192.0.2.1"): response(
                answer=[rr("www.example.test", "A", "192.0.2.9")], aa=True),
        })
        address, path = r.resolve("www.example.test")
        self.assertEqual(address, "192.0.2.9")
        self.assertEqual(path, [root, root, "192.0.2.1"])
        fallback = self.make_resolver({
            ("example.test", ROOT_SERVERS[1]): response(
                answer=[rr("example.test", "A", "192.0.2.9")], aa=True)})
        self.assertEqual(fallback.resolve("example.test")[1], ROOT_SERVERS[:2])

    def test_cname_restarts_and_rejects_loop(self):
        root = ROOT_SERVERS[0]
        records = {
            ("a.test", root): response(answer=[rr("a.test", "CNAME", "b.test")], aa=True),
            ("b.test", root): response(answer=[rr("b.test", "A", "192.0.2.9")], aa=True)}
        self.assertEqual(self.make_resolver(records).resolve("a.test")[0], "192.0.2.9")
        records[("b.test", root)] = response(answer=[rr("b.test", "CNAME", "a.test")], aa=True)
        with self.assertRaises(RuntimeError):
            self.make_resolver(records).resolve("a.test")

    def test_glue_and_query_budget(self):
        root = ROOT_SERVERS[0]
        records = {
            ("www.test", root): response(authority=[rr("test", "NS", "ns.test")],
                additional=[rr("ns.test", "A", "192.0.2.1")]),
            ("www.test", "192.0.2.1"): response(answer=[rr("www.test", "A", "192.0.2.9")], aa=True)}
        self.assertEqual(self.make_resolver(records).resolve("www.test")[1], [root, "192.0.2.1"])
        with self.assertRaises(RuntimeError):
            self.make_resolver(records, max_queries=1).resolve("www.test")

    def test_section_parser(self):
        text = """;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 1
;; flags: qr aa; QUERY: 1
;; ANSWER SECTION:
example.test. 42 IN A 192.0.2.8
"""
        parsed = parse_response(text)
        self.assertTrue(parsed["aa"])
        self.assertEqual(parsed["answer"][0]["value"], "192.0.2.8")

    def test_cross_tld_root_glue(self):
        root = ROOT_SERVERS[0]
        records = {
            ("example.com", root): response(authority=[rr("com", "NS", "ns.example.net")],
                additional=[rr("ns.example.net", "A", "192.0.2.1")]),
            ("example.com", "192.0.2.1"): response(
                answer=[rr("example.com", "A", "192.0.2.9")], aa=True)}
        self.assertEqual(self.make_resolver(records).resolve("example.com")[1],
                         [root, "192.0.2.1"])


if __name__ == "__main__":
    unittest.main()
