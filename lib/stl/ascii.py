
from stl.types import *


class KeywordToken(str):
    pass


class NumberToken(float):
    pass


def _token_type_name(token_type):
    NoneType = type(None)
    if token_type is NoneType:
        return 'end of file'
    elif token_type is KeywordToken:
        return 'keyword'
    elif token_type is NumberToken:
        return 'number'
    else:
        return 'unknown'


class Scanner(object):

    def __init__(self, file):
        self.file = file
        self.peeked = None
        self.peeked_byte = None
        self.peeked_col = 0
        self.peeked_row = 1

    def peek_byte(self):
        if self.peeked_byte is None:
            self.peeked_byte = self.file.read(1)
            if self.peeked_byte == '\n':
                self.peeked_row += 1
                self.peeked_col = 0
            else:
                self.peeked_col += 1

        return self.peeked_byte

    def get_byte(self):
        byte = self.peek_byte()
        self.peeked_byte = None
        return byte

    def peek_token(self):
        while self.peeked is None:
            b = self.peek_byte()
            self.token_start_row = self.peeked_row
            self.token_start_col = self.peeked_col

            if b == '':
                return None
            elif b.isalpha() or b == '_':
                self.peeked = self._read_keyword()
            elif b.isdigit() or b == '.' or b == '-':
                self.peeked = self._read_number()
            elif b.isspace():
                # Just skip over spaces
                self.get_byte()
                continue
            else:
                raise SyntaxError(
                    "Invalid character %r at line %i, column %i" % (
                        b, self.peeked_row, self.peeked_col
                    )
                )

        return self.peeked

    def get_token(self):
        token = self.peek_token()
        self.peeked = None
        return token

    def require_token(self, token_type, required_value=None):
        token = self.get_token()
        if isinstance(token, token_type):
            if required_value is None or token == required_value:
                return token
            else:
                got_token_type = _token_type_name(type(token))
                expected_token_type = _token_type_name(token_type)
                raise SyntaxError(
                    "Expected %s %r but got %s %r at line %i, column %i" % (
                        expected_token_type,
                        required_value,
                        got_token_type,
                        token,
                        self.token_start_row,
                        self.token_start_col,
                    )
                )
        else:
            got_token_type = _token_type_name(type(token))
            expected_token_type = _token_type_name(token_type)
            raise SyntaxError(
                "Expected %s but got %s at line %i, column %i" % (
                    expected_token_type,
                    got_token_type,
                    self.token_start_row,
                    self.token_start_col,
                )
            )

    def _read_keyword(self):
        ret_bytes = []
        start_row = self.peeked_row
        start_col = self.peeked_col
        while True:
            b = self.peek_byte()
            if b.isalpha() or b == '_' or b.isdigit():
                ret_bytes.append(self.get_byte())
            else:
                break

        ret = KeywordToken(''.join(ret_bytes))

        ret.start_row = start_row
        ret.start_col = start_col

        return ret

    def _read_number(self):
        ret_bytes = []
        start_row = self.peeked_row
        start_col = self.peeked_col
        while True:
            b = self.peek_byte()
            if b.isdigit() or b in ('.', '+', '-', 'e', 'E'):
                ret_bytes.append(self.get_byte())
            else:
                break

        try:
            ret = NumberToken(''.join(ret_bytes))
        except ValueError:
            raise SyntaxError(
                "Invalid float number at line %i, column %i" % (
                    start_row, start_col,
                )
            )

        ret.start_row = start_row
        ret.start_col = start_col

        return ret


class SyntaxError(ValueError):
    pass


def parse(file):
    scanner = Scanner(file)

    scanner.require_token(KeywordToken, "solid")
    name = str(scanner.require_token(KeywordToken))

    ret = Solid(name=name)

    def parse_facet():
        scanner.require_token(KeywordToken, "facet")
        scanner.require_token(KeywordToken, "normal")
        normal_x = scanner.require_token(NumberToken)
        normal_y = scanner.require_token(NumberToken)
        normal_z = scanner.require_token(NumberToken)
        normal = Vector3d(
            x=normal_x,
            y=normal_y,
            z=normal_z,
        )

        scanner.require_token(KeywordToken, "outer")
        scanner.require_token(KeywordToken, "loop")
        vertices = []
        for i in xrange(0, 3):
            scanner.require_token(KeywordToken, "vertex")
            vertex_x = scanner.require_token(NumberToken)
            vertex_y = scanner.require_token(NumberToken)
            vertex_z = scanner.require_token(NumberToken)
            vertices.append(
                Vector3d(
                    x=vertex_x,
                    y=vertex_y,
                    z=vertex_z,
                )
            )

        ret = Facet(
            normal=normal,
            vertices=vertices,
        )

        scanner.require_token(KeywordToken, "endloop")
        scanner.require_token(KeywordToken, "endfacet")

        return ret

    while True:
        token = scanner.peek_token()
        token_type = type(token)

        if token_type is KeywordToken and token == 'endsolid':
            break
        elif token_type is KeywordToken and token == 'facet':
            facet = parse_facet()
            ret.facets.append(facet)
        else:
            got_token_type = _token_type_name(token_type)
            expected_token_type = _token_type_name(token_type)
            raise SyntaxError(
                "Unexpected %s %r at line %i, column %i" % (
                    got_token_type,
                    token,
                    token.start_row,
                    token.start_col,
                )
            )

    scanner.require_token(KeywordToken, "endsolid")
    end_name = str(scanner.require_token(KeywordToken))
    if name != end_name:
        raise SyntaxError(
            "Solid started named %r but ended named %r" % (
                name, end_name,
            )
        )

    return ret


def write(solid, file):
    name = solid.name
    if name is None:
        name = "unnamed"

    file.write("solid %s\n" % name)
    for facet in solid.facets:
        file.write("  facet normal %g %g %g\n" % facet.normal)
        file.write("    outer loop\n")
        for vertex in facet.vertices:
            file.write("      vertex %g %g %g\n" % vertex)
        file.write("    endloop\n")
        file.write("  endfacet\n")
    file.write("endsolid %s\n" % name)
