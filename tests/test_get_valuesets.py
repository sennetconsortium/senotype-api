def test_get_valuesets_with_predicate(app):
    with app.test_client() as client:
        res = client.get("/valuesets?predicate_term=taxon")

        assert res.status_code == 200

        terms = sorted([valueset["term"] for valueset in res.json["valuesets"]])
        assert len(terms) == 2
        assert terms[0] == "human"
        assert terms[1] == "mouse"


def test_get_all_valuesets(app):
    with app.test_client() as client:
        res = client.get("/valuesets")

        assert res.status_code == 200
        assert len(res.json["valuesets"]) == 73


def test_get_nonexistent_valuesets(app):
    with app.test_client() as client:
        res = client.get("/valuesets?predicate_term=nonexistent")

        assert res.status_code == 200
        assert len(res.json["valuesets"]) == 0
