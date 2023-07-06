from oes.registration.auth.scope import Scope, Scopes


def test_scope_set_operations():
    s1 = Scopes(("a", "b", "c"))
    s2 = Scopes(("c",))

    assert s1 > s2
    assert s1 & s2 == s2
    assert isinstance((s1 & {"c"}), Scopes)
    assert (s1 & frozenset()) == Scopes()
    assert "c" in s2
    assert "d" not in s2
    assert s1 & Scopes(("d",)) == Scopes()


def test_scopes_constructor():
    s1 = Scopes("a b c")
    s2 = Scopes(("b", "c", "a"))
    assert s1 == s2

    s3 = Scopes(s1)
    assert s3._set is s1._set


def test_scopes_str():
    s = Scopes("c a b")
    assert str(s) == "a b c"


def test_scopes_enum():
    s = Scopes((Scope.event, Scope.cart))
    assert str(s) == "cart event"
