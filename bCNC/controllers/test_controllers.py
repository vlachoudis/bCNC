from _GenericController import POSPAT, STATUSPAT


def test_pospat():
    class Test:
        def __init__(self, **entries): self.__dict__.update(entries)
        input = ""
        expected = []

    for t in [
        Test(input="[PRB:-356.0,-5.28,-118.3]", expected=("PRB", "-356.0", "-5.28", "-118.3", None, None, None)),
        Test(input="[PRB:-356.0,-5.28,-118.3,4.0]", expected=("PRB", "-356.0", "-5.28", "-118.3", "4.0", None, None)),
        Test(input="[PRB:-356.0,-5.28,-118.3,4.0,5.0]", expected=("PRB", "-356.0", "-5.28", "-118.3", "4.0", "5.0", None)),
        Test(input="[PRB:-356.0,-5.28,-118.3,4.0,5.0,6.0]", expected=("PRB", "-356.0", "-5.28", "-118.3", "4.0", "5.0", "6.0")),
        Test(input="[PRB:-356.0,-5.28,-118.3:0]", expected=("PRB", "-356.0", "-5.28", "-118.3", None, None, None)),
        Test(input="[PRB:-356.0,-5.28,-118.3:1]", expected=("PRB", "-356.0", "-5.28", "-118.3", None, None, None)),
        Test(input="[PRB:-356.0,-5.28,-118.3:12]", expected=("PRB", "-356.0", "-5.28", "-118.3", None, None, None)),
        Test(input="[PRB:-356.0,-5.28,-118.3,4.0:1]", expected=("PRB", "-356.0", "-5.28", "-118.3", "4.0", None, None)),
        Test(input="[PRB:-356.0,-5.28,-118.3,4.0,5.0:2]", expected=("PRB", "-356.0", "-5.28", "-118.3", "4.0", "5.0", None)),
        Test(input="[PRB:-356.0,-5.28,-118.3,4.0,5.0,6.0:3]", expected=("PRB", "-356.0", "-5.28", "-118.3", "4.0", "5.0", "6.0")),
    ]:
        got = POSPAT.match(t.input)
        assert got != None, "input %s should match, but didn't" % t.input
        assert got.groups() == t.expected, "input %s should result in %s, but got %s" % (t.input, t.expected, got.groups())


if __name__ == '__main__':
    test_pospat()
