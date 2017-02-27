
from PySide.QtGui import QVBoxLayout, QMenu, QApplication
from PySide.QtCore import Qt, QSize

from ...utils import locate_function
from ...data.function_graph import FunctionGraph
from ..widgets import QDisasmGraph, QDisasmStatusBar
from ..dialogs.jumpto import JumpTo
from ..dialogs.rename_label import RenameLabel
from ..dialogs.new_path import NewPath
from ..menus.disasm_insn_context_menu import DisasmInsnContextMenu
from .view import BaseView


class JumpHistory(object):
    def __init__(self):
        self._history = [ ]
        self._pos = 0

    def __len__(self):
        return len(self._history)

    def jump_to(self, addr):

        if self._pos != len(self._history) - 1:
            self.trim()

        if not self._history or self._history[-1] != addr:
            self._history.append(addr)
            self._pos = len(self._history) - 1

    def trim(self):
        self._history = self._history[ : self._pos + 1]

    def backtrack(self):
        if self._pos > 0:
            self._pos -= 1

        if self._pos >= len(self._history):
            return None
        else:
            return self._history[self._pos]

    def forwardstep(self):
        if self._pos < len(self._history) - 1:
            self._pos += 1

        if self._pos < len(self._history):
            return self._history[self._pos]
        else:
            return None


class DisassemblyView(BaseView):
    def __init__(self, workspace, *args, **kwargs):
        super(DisassemblyView, self).__init__('disassembly', workspace, *args, **kwargs)

        self.caption = 'Disassembly'

        self._flow_graph = None
        self._statusbar = None
        self._jump_history = JumpHistory()

        self._insn_menu = None

        self._insn_addr_on_context_menu = None

        self._init_widgets()
        self._init_menus()

    def reload(self):
        pass

    #
    # Properties
    #

    @property
    def disasm(self):
        return self._flow_graph.disasm

    #
    # UI
    #

    def instruction_context_menu(self, insn, pos):

        self._insn_addr_on_context_menu = insn.addr

        # pass in the instruction address
        self._insn_menu.insn_addr = insn.addr
        # pop up the menu
        self._insn_menu.qmenu().exec_(pos)

        self._insn_addr_on_context_menu = None

    def popup_jumpto_dialog(self):
        JumpTo(self, None).exec_()

    def popup_rename_label_dialog(self):
        label_addr = self._address_in_selection()
        if label_addr is None:
            return

        dialog = RenameLabel(self, label_addr, None)
        dialog.exec_()

    def popup_newpath_dialog(self):
        addr = self._address_in_selection()
        if addr is None:
            return

        dialog = NewPath(self.workspace, addr, parent=None)
        dialog.exec_()

    #
    # Public methods
    #

    def display_function(self, function):

        self._jump_history.jump_to(function.addr)
        self._display_function(function)

    def toggle_instruction_selection(self, insn_addr):
        """
        Toggle the selection state of an instruction in the disassembly view.

        :param int insn_addr: Address of the instruction to toggle.
        :return:              None
        """

        if insn_addr in self._flow_graph.selected_insns:
            self._flow_graph.unselect_instruction(insn_addr)
        else:
            self._flow_graph.select_instruction(insn_addr, unique=QApplication.keyboardModifiers() & Qt.CTRL == 0)
            self._flow_graph.show_instruction(insn_addr)

    def jump_to(self, addr):
        self._jump_history.jump_to(addr)
        self._jump_to(addr)

    def jump_back(self):
        addr = self._jump_history.backtrack()
        if addr is not None:
            self._jump_to(addr)

    def jump_forward(self):
        addr = self._jump_history.forwardstep()
        if addr is not None:
            self._jump_to(addr)

    def rename_label(self, addr, new_name):
        if self._flow_graph.disasm is not None:
            kb = self._flow_graph.disasm.kb
            if new_name == '':
                if addr in kb.labels:
                    del kb.labels[addr]
            else:
                kb.labels[addr] = new_name

            # redraw the current block
            self._flow_graph.update_label(addr)

    def sizeHint(self):
        return QSize(800, 800)

    #
    # Initialization
    #

    def _init_widgets(self):

        self._flow_graph = QDisasmGraph(self.workspace, self)

        self._statusbar = QDisasmStatusBar(self)

        hlayout = QVBoxLayout()
        hlayout.addWidget(self._flow_graph)
        hlayout.addWidget(self._statusbar)

        self.setLayout(hlayout)

    def _init_menus(self):

        self._insn_menu = DisasmInsnContextMenu(self)

    #
    # Private methods
    #

    def _display_function(self, function):

        # set status bar
        self._statusbar.function = function

        if self._flow_graph.function_graph is None or self._flow_graph.function_graph.function is not function:
            # clear existing selected instructions
            self._flow_graph.selected_insns.clear()
            # set function graph of a new function
            self._flow_graph.function_graph = FunctionGraph(function=function)
        else:
            # still use the current function. just unselect existing selections.
            self._flow_graph.unselect_all_instructions()

    def _jump_to(self, addr):
        function = locate_function(self.workspace.instance, addr)
        if function is not None:
            self._display_function(function)
            self.toggle_instruction_selection(addr)
            return True
        else:
            return False

    #
    # Utils
    #

    def _address_in_selection(self):
        if self._insn_addr_on_context_menu is not None:
            return self._insn_addr_on_context_menu
        elif len(self._flow_graph.selected_insns) == 1:
            return next(iter(self._flow_graph.selected_insns))
        else:
            return None