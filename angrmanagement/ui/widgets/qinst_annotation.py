from typing import TYPE_CHECKING
from PySide2.QtGui import QColor, QPainterPath, QBrush, QCursor
from PySide2.QtCore import QMarginsF
from PySide2.QtWidgets import QGraphicsItem, QGraphicsSimpleTextItem, QGraphicsSceneMouseEvent, QMenu, QInputDialog, QLineEdit

from .qsimulation_managers import QSimulationManagers
from ...logic import GlobalInfo
from ...config import Conf

if TYPE_CHECKING:
    from ..views.symexec_view import SymexecView
    from ..views.disassembly_view import DisassemblyView


class QInstructionAnnotation(QGraphicsSimpleTextItem):
    """
    Abstract Instruction Annotation Class.
    It must have address prop to show at the right place.
    """

    background_color = None
    foreground_color = None
    addr = None
    _config = Conf

    def __init__(self, addr, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addr = addr
        self.setBrush(QBrush(self.foreground_color))
        self.setFont(self._config.disasm_font)

    def paint(self, painter, *args, **kwargs):
        margin = QMarginsF(3, 0, 3, 0)
        box = self.boundingRect().marginsAdded(margin)
        path = QPainterPath()
        path.addRoundedRect(box, 3, 3)
        painter.fillPath(path, self.background_color)
        super().paint(painter, *args, **kwargs)


class QStatsAnnotation(QInstructionAnnotation):
    """
    Abstract Stats Annotation Class.
    """

    def __init__(self, addr,  *args, **kwargs):
        super().__init__(addr, *args, **kwargs)
        self.setAcceptHoverEvents(True)
        self.disasm_view = GlobalInfo.main_window.workspace.view_manager.first_view_in_category(
            "disassembly")  # type: DisassemblyView
        self.symexec_view = GlobalInfo.main_window.workspace.view_manager.first_view_in_category(
            "symexec")  # type: SymexecView
        self.hovered = False

    def mousePressEvent(self, event):
        pass

    def hoverEnterEvent(self, event): #pylint: disable=unused-argument
        self.hovered = True
        self.disasm_view.redraw_current_graph()

    def hoverLeaveEvent(self, event): #pylint: disable=unused-argument
        self.hovered = False
        self.disasm_view.redraw_current_graph()

    def paint(self, painter, *args, **kwargs):
        if self.hovered:
            margin = QMarginsF(7, 5, 7, 5)
        else:
            margin = QMarginsF(3, 0, 3, 0)
        box = self.boundingRect().marginsAdded(margin)
        path = QPainterPath()
        path.addRoundedRect(box, 5, 5)
        painter.fillPath(path, self.background_color)
        super().paint(painter, *args, **kwargs)


class QActiveCount(QStatsAnnotation):
    """
    Indicating how much active states are in these address.
    We can select/move the set of states.
    Used by execution_statistics_viewer plugin.
    """
    background_color = QColor(0, 255, 0, 30)
    foreground_color = QColor(0, 60, 0)

    def __init__(self, addr, states):
        super().__init__(addr, str(len(states)))
        self.states = states

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:  #pylint: disable=unused-argument
        menu = QMenu()

        def _select_states():
            self.symexec_view.select_states(self.states)
            self.disasm_view.workspace.raise_view(self.symexec_view)

        def _move_states():
            to_stash, ok = QInputDialog.getText(self.disasm_view, "Move to?", "Target Stash Name:", QLineEdit.Normal)
            if ok:
                self.symexec_view.current_simgr.move("active", to_stash, lambda s: s in self.states)
                self.disasm_view.refresh()
                self.symexec_view._simgrs._simgr_viewer.refresh()

        menu.addAction("Select", _select_states)
        menu.addAction("Move To", _move_states)
        menu.exec_(QCursor.pos())


class QPassthroughCount(QStatsAnnotation):
    """
    Indicating how much states passthrough address.
    Used by execution_statistics_viewer plugin.
    """
    background_color = QColor(255, 0, 0, 30)
    foreground_color = QColor(60, 0, 0)

    def __init__(self, addr, count):
        super().__init__(addr, str(count))

    # def mousePressEvent(self, event):
    #     self.symexec_view.select_states_that_passed_through(self.addr)
    #     self.disasm_view.workspace.raise_view(self.symexec_view)


class QHookAnnotation(QInstructionAnnotation):
    """
    An instruction annotation for an angr project hook.
    It is added to the annotation list by fetch_qblock_annotations and
    displays an indicator next to hooked blocks.
    """
    background_color = QColor(230, 230, 230)
    foreground_color = QColor(50, 50, 50)

    def __init__(self, disasm_view: 'DisassemblyView', addr, *args, **kwargs):
        super().__init__(addr, "hook", *args, **kwargs)
        self.disasm_view = disasm_view

    def contextMenuEvent(self, event): #pylint: disable=unused-argument
        menu = QMenu()
        menu.addAction("Delete", self.delete)
        menu.exec_(QCursor.pos())

    def delete(self):
        self.disasm_view.workspace.instance.delete_hook(self.addr)
        self.disasm_view.refresh()


class QExploreAnnotation(QInstructionAnnotation):
    """
    Abstract Class for find and avoid
    """

    background_color = None
    foreground_color = QColor(230, 230, 230)
    text = None

    def __init__(self, addr, disasm_view, qsimgrs: QSimulationManagers, *args, **kwargs):
        super().__init__(addr, self.text, *args, **kwargs)
        self.disasm_view = disasm_view
        self.qsimgrs = qsimgrs

    def contextMenuEvent(self, event): #pylint: disable=unused-argument
        menu = QMenu()
        menu.addAction("Delete", self.delete)
        menu.exec_(QCursor.pos())

    def delete(self):
        raise NotImplementedError


class QFindAddrAnnotation(QExploreAnnotation):
    """
    An instruction annotation for explore find address.
    It is added to the annotation list by fetch_qblock_annotations
    """
    background_color = QColor(200, 230, 100)
    foreground_color = QColor(30, 80, 30)
    text = "find"

    def delete(self):
        self.qsimgrs.remove_find_address(self.addr)
        self.disasm_view.refresh()


class QAvoidAddrAnnotation(QExploreAnnotation):
    """
    An instruction annotation for explore avoid address.
    It is added to the annotation list by fetch_qblock_annotations
    """
    background_color = QColor(230, 200, 100)
    foreground_color = QColor(80, 30, 30)
    text = "avoid"

    def delete(self):
        self.qsimgrs.remove_avoid_address(self.addr)
        self.disasm_view.refresh()


class QBlockAnnotations(QGraphicsItem):
    """
    Container for all instruction annotations in a QBlock
    """

    PADDING = 10

    def __init__(self, addr_to_annotations: dict, *, parent):
        super().__init__(parent=parent)
        self.addr_to_annotations = addr_to_annotations
        max_width = 0
        for _addr, annotations in self.addr_to_annotations.items():
            width = sum(a.boundingRect().width() + self.PADDING for a in annotations)
            max_width = max(max_width, width)
            for annotation in annotations:
                annotation.setParentItem(self)
        self.width = max_width
        self._init_widgets()

    def get(self, addr):
        return self.addr_to_annotations.get(addr)

    def paint(self, painter, *args, **kwargs):
        pass

    def boundingRect(self):
        return self.childrenBoundingRect()

    def _init_widgets(self):
        # Set the x positions of all the annotations. The y positions will be set later while laying out the
        # instructions
        for _addr, annotations in self.addr_to_annotations.items():
            x = self.width
            for annotation in annotations:
                annotation.setX(x - annotation.boundingRect().width())
                x -= annotation.boundingRect().width() + self.PADDING