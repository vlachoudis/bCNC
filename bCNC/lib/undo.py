#
# Copyright and User License
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copyright Vasilis.Vlachoudis@cern.ch for the
# European Organization for Nuclear Research (CERN)
#
# DISCLAIMER
# ~~~~~~~~~~
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
# NOT LIMITED TO, IMPLIED WARRANTIES OF MERCHANTABILITY, OF
# SATISFACTORY QUALITY, AND FITNESS FOR A PARTICULAR PURPOSE
# OR USE ARE DISCLAIMED. THE COPYRIGHT HOLDERS AND THE
# AUTHORS MAKE NO REPRESENTATION THAT THE SOFTWARE AND
# MODIFICATIONS THEREOF, WILL NOT INFRINGE ANY PATENT,
# COPYRIGHT, TRADE SECRET OR OTHER PROPRIETARY RIGHT.
#
# LIMITATION OF LIABILITY
# ~~~~~~~~~~~~~~~~~~~~~~~
# THE COPYRIGHT HOLDERS AND THE AUTHORS SHALL HAVE NO
# LIABILITY FOR DIRECT, INDIRECT, SPECIAL, INCIDENTAL,
# CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES OF ANY
# CHARACTER INCLUDING, WITHOUT LIMITATION, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES, LOSS OF USE, DATA OR PROFITS,
# OR BUSINESS INTERRUPTION, HOWEVER CAUSED AND ON ANY THEORY
# OF CONTRACT, WARRANTY, TORT (INCLUDING NEGLIGENCE), PRODUCT
# LIABILITY OR OTHERWISE, ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
#
# Author:    Vasilis.Vlachoudis@cern.ch


# =============================================================================
# Undo Redo Class
# =============================================================================
class UndoRedo:
    # -----------------------------------------------------------------------
    def __init__(self):
        self.undoList = []
        self.redoList = []

    # -----------------------------------------------------------------------
    def reset(self):
        del self.undoList[:]
        del self.redoList[:]

    # -----------------------------------------------------------------------
    # Add undoinfo as (msg, func/list, args)
    # -----------------------------------------------------------------------
    def add(self, undoinfo, msg=None):
        if not undoinfo:
            return
        if msg is not None:
            if isinstance(undoinfo[0], str):
                # replace message
                undoinfo = (msg,) + undoinfo[1:]
            elif isinstance(undoinfo, tuple):
                undoinfo = (msg,) + undoinfo
            else:
                undoinfo = (msg, undoinfo)
            f = 1
        else:
            f = int(isinstance(undoinfo[0], str))
        assert (
            isinstance(undoinfo, list)
            or callable(undoinfo[f])
            or isinstance(undoinfo[f], list)
        )
        self.undoList.append(undoinfo)
        del self.redoList[:]

    # -----------------------------------------------------------------------
    # Split the undoinfo into [msg, ]func/list [, args]
    # msg can exists or not check for str/unicode
    # func can be a list or an executable
    # if func is a list then there are no args
    # @return always a tuple of 3 with msg, func, args
    # -----------------------------------------------------------------------
    @staticmethod
    def _split(undoinfo):
        if isinstance(undoinfo, list):
            return None, undoinfo, None
        elif undoinfo[0] is None or isinstance(undoinfo[0], str):
            assert callable(undoinfo[1]) or isinstance(undoinfo[1], list)
            return undoinfo[0], undoinfo[1], undoinfo[2:]
        else:
            assert callable(undoinfo[0]) or isinstance(undoinfo[0], list)
            return None, undoinfo[0], undoinfo[1:]

    # -----------------------------------------------------------------------
    # Execute the undoinfo and return the redoinfo
    # -----------------------------------------------------------------------
    def _execute(self, undoinfo):
        if undoinfo is None:
            return None
        msg, func, args = UndoRedo._split(undoinfo)
        if isinstance(func, list):
            redolist = []
            while func:
                redolist.append(self._execute(func.pop()))
            if msg:
                return msg, redolist
            else:
                return redolist
        else:
            redoinfo = func(*args)
            if isinstance(redoinfo[0], str):
                return redoinfo
            elif msg:
                return (msg,) + redoinfo
            else:
                return redoinfo

    # -----------------------------------------------------------------------
    def undo(self):
        if not self.undoList:
            return
        self.redoList.append(self._execute(self.undoList.pop()))

    # -----------------------------------------------------------------------
    def redo(self):
        if not self.redoList:
            return
        self.undoList.append(self._execute(self.redoList.pop()))

    # -----------------------------------------------------------------------
    def canUndo(self):
        return bool(self.undoList)

    # -----------------------------------------------------------------------
    def canRedo(self):
        return bool(self.redoList)

    # -----------------------------------------------------------------------
    def undoText(self):
        u = self.undoList[-1]
        if isinstance(u[0], str):
            return u[0]
        else:
            return "undo"

    # -----------------------------------------------------------------------
    def undoTextList(self):
        lst = []
        for u in self.undoList:
            if isinstance(u[0], str):
                lst.append(u[0])
            else:
                lst.append("undo")
        lst.reverse()
        return lst
