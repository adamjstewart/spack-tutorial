##############################################################################
# Copyright (c) 2013-2016, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Spack.
# Created by Todd Gamblin, tgamblin@llnl.gov, All rights reserved.
# LLNL-CODE-647188
#
# For details, see https://github.com/llnl/spack
# Please also see the NOTICE and LICENSE files for our notice and the LGPL.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License (as
# published by the Free Software Foundation) version 2.1, February 1999.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the IMPLIED WARRANTY OF
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the terms and
# conditions of the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##############################################################################
"""
This file implements an expression syntax, similar to ``printf``, for adding
ANSI colors to text.

See ``colorize()``, ``cwrite()``, and ``cprint()`` for routines that can
generate colored output.

``colorize`` will take a string and replace all color expressions with
ANSI control codes.  If the ``isatty`` keyword arg is set to False, then
the color expressions will be converted to null strings, and the
returned string will have no color.

``cwrite`` and ``cprint`` are equivalent to ``write()`` and ``print()``
calls in python, but they colorize their output.  If the ``stream`` argument is
not supplied, they write to ``sys.stdout``.

Here are some example color expressions:

==========  ============================================================
Expression  Meaning
==========  ============================================================
@r          Turn on red coloring
@R          Turn on bright red coloring
@*{foo}     Bold foo, but don't change text color
@_{bar}     Underline bar, but don't change text color
@*b         Turn on bold, blue text
@_B         Turn on bright blue text with an underline
@.          Revert to plain formatting
@*g{green}  Print out 'green' in bold, green text, then reset to plain.
@*ggreen@.  Print out 'green' in bold, green text, then reset to plain.
==========  ============================================================

The syntax consists of:

==========  =================================================
color-expr  '@' [style] color-code '{' text '}' | '@.' | '@@'
style       '*' | '_'
color-code  [krgybmcwKRGYBMCW]
text        .*
==========  =================================================

'@' indicates the start of a color expression.  It can be followed
by an optional * or _ that indicates whether the font should be bold or
underlined.  If * or _ is not provided, the text will be plain.  Then
an optional color code is supplied.  This can be [krgybmcw] or [KRGYBMCW],
where the letters map to  black(k), red(r), green(g), yellow(y), blue(b),
magenta(m), cyan(c), and white(w).  Lowercase letters denote normal ANSI
colors and capital letters denote bright ANSI colors.

Finally, the color expression can be followed by text enclosed in {}.  If
braces are present, only the text in braces is colored.  If the braces are
NOT present, then just the control codes to enable the color will be output.
The console can be reset later to plain text with '@.'.

To output an @, use '@@'.  To output a } inside braces, use '}}'.
"""
import re
import sys


class ColorParseError(Exception):
    """Raised when a color format fails to parse."""

    def __init__(self, message):
        super(ColorParseError, self).__init__(message)


# Text styles for ansi codes
styles = {'*': '1',       # bold
          '_': '4',       # underline
          None: '0'}      # plain

# Dim and bright ansi colors
colors = {'k': 30, 'K': 90,  # black
          'r': 31, 'R': 91,  # red
          'g': 32, 'G': 92,  # green
          'y': 33, 'Y': 93,  # yellow
          'b': 34, 'B': 94,  # blue
          'm': 35, 'M': 95,  # magenta
          'c': 36, 'C': 96,  # cyan
          'w': 37, 'W': 97}  # white

# Regex to be used for color formatting
color_re = r'@(?:@|\.|([*_])?([a-zA-Z])?(?:{((?:[^}]|}})*)})?)'


# Force color even if stdout is not a tty.
_force_color = False


class match_to_ansi(object):

    def __init__(self, color=True):
        self.color = color

    def escape(self, s):
        """Returns a TTY escape sequence for a color"""
        if self.color:
            return "\033[%sm" % s
        else:
            return ''

    def __call__(self, match):
        """Convert a match object generated by ``color_re`` into an ansi
        color code. This can be used as a handler in ``re.sub``.
        """
        style, color, text = match.groups()
        m = match.group(0)

        if m == '@@':
            return '@'
        elif m == '@.':
            return self.escape(0)
        elif m == '@':
            raise ColorParseError("Incomplete color format: '%s' in %s"
                                  % (m, match.string))

        string = styles[style]
        if color:
            if color not in colors:
                raise ColorParseError("invalid color specifier: '%s' in '%s'"
                                      % (color, match.string))
            string += ';' + str(colors[color])

        colored_text = ''
        if text:
            colored_text = text + self.escape(0)

        return self.escape(string) + colored_text


def colorize(string, **kwargs):
    """Replace all color expressions in a string with ANSI control codes.

    Args:
        string (str): The string to replace

    Returns:
        str: The filtered string

    Keyword Arguments:
        color (bool): If False, output will be plain text without control
            codes, for output to non-console devices.
    """
    color = kwargs.get('color', True)
    return re.sub(color_re, match_to_ansi(color), string)


def clen(string):
    """Return the length of a string, excluding ansi color sequences."""
    return len(re.sub(r'\033[^m]*m', '', string))


def cextra(string):
    """"Length of extra color characters in a string"""
    return len(''.join(re.findall(r'\033[^m]*m', string)))


def cwrite(string, stream=sys.stdout, color=None):
    """Replace all color expressions in string with ANSI control
       codes and write the result to the stream.  If color is
       False, this will write plain text with o color.  If True,
       then it will always write colored output.  If not supplied,
       then it will be set based on stream.isatty().
    """
    if color is None:
        color = stream.isatty() or _force_color
    stream.write(colorize(string, color=color))


def cprint(string, stream=sys.stdout, color=None):
    """Same as cwrite, but writes a trailing newline to the stream."""
    cwrite(string + "\n", stream, color)


def cescape(string):
    """Replace all @ with @@ in the string provided."""
    return str(string).replace('@', '@@')


class ColorStream(object):

    def __init__(self, stream, color=None):
        self._stream = stream
        self._color = color

    def write(self, string, **kwargs):
        raw = kwargs.get('raw', False)
        raw_write = getattr(self._stream, 'write')

        color = self._color
        if self._color is None:
            if raw:
                color = True
            else:
                color = self._stream.isatty() or _force_color
        raw_write(colorize(string, color=color))

    def writelines(self, sequence, **kwargs):
        raw = kwargs.get('raw', False)
        for string in sequence:
            self.write(string, self.color, raw=raw)