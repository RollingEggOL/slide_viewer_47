import typing
from PyQt5 import QtCore, QtGui

import PyQt5
import openslide
from PyQt5.QtCore import QPoint, Qt, QEvent, QRect, QSize, QRectF, pyqtSignal, QMarginsF, QSizeF, QPointF
from PyQt5.QtGui import QWheelEvent, QMouseEvent, QImage, QPainter, QTransform, QResizeEvent, QPaintEvent
from PyQt5.QtWidgets import QWidget, QGraphicsView, QGraphicsScene, QVBoxLayout, QLabel, QRubberBand, QGraphicsItem

from slide_viewer_47.graphics.graphics_tile import GraphicsTile
from slide_viewer_47.graphics.slide_graphics_group import SlideGraphicsGroup
from slide_viewer_47.common.utils import point_to_str, SlideHelper


def build_screenshot_image(scene: QGraphicsScene, image_size: QSize, scene_rect: QRectF = QRectF()) -> QImage:
    # pixmap = self.view.viewport().grab()
    # pixmap.save("view_screenshot.png")
    image = QImage(image_size, QImage.Format_RGBA8888)
    painter = QPainter(image)
    # painter.setClipping(True)
    # painter.setClipRect(QRect(QPoint(0, 0), image_size))
    image.fill(painter.background().color())
    # if not scene_rect:
    #     scene_rect = scene.sceneRect()
    # scene.setSceneRect(scene_rect)
    items1 = scene.items(scene_rect, Qt.IntersectsItemBoundingRect)
    all_items = scene.items()
    # for item in all_items:
    #     if isinstance(item, GraphicsTile):
    #         item.setVisible(False)
    # for item in items1:
    #     item.setVisible(True)
    print(items1)
    items2 = scene.items(scene_rect, Qt.IntersectsItemBoundingRect)
    print(items2)
    top_level_items = [item.topLevelItem() for item in items1]
    print("before render==========================================")
    rendered_size = scene_rect.size().scaled(QSizeF(image_size), Qt.KeepAspectRatio)
    dsize = QSizeF(image_size) - rendered_size
    top_left = QPointF(dsize.width() / 2, dsize.height() / 2)
    scene.render(painter, QRectF(top_left, rendered_size), scene_rect)
    painter.end()
    return image


class MyScene(QGraphicsScene):

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)

    # def items(self, rect: QtCore.QRectF, mode: QtCore.Qt.ItemSelectionMode = ..., order: QtCore.Qt.SortOrder = ...,
    #           deviceTransform: QtGui.QTransform = ...) -> typing.List[QGraphicsItem]:
    #     return super().items(rect, mode, order, deviceTransform)


#

class SlideViewer(QWidget):
    eventSignal = pyqtSignal(PyQt5.QtCore.QEvent)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.init_view()
        self.init_labels()
        self.init_layout()

    def init_view(self):
        self.scene = MyScene()
        self.view = QGraphicsView()
        self.view.setScene(self.scene)
        self.view.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.view.viewport().installEventFilter(self)

        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self.mouse_press_view = QPoint()

        self.view.horizontalScrollBar().sliderMoved.connect(self.update_labels)
        self.view.verticalScrollBar().sliderMoved.connect(self.update_labels)

    def init_labels(self):
        self.level_label = QLabel()
        self.level_label.setWordWrap(True)
        self.selected_rect_label = QLabel()
        self.selected_rect_label.setWordWrap(True)
        self.mouse_pos_scene_label = QLabel()
        self.mouse_pos_scene_label.setWordWrap(True)
        self.view_rect_scene_label = QLabel()
        self.view_rect_scene_label.setWordWrap(True)

    def init_layout(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        layout.addWidget(self.level_label)
        layout.addWidget(self.mouse_pos_scene_label)
        # layout.addWidget(self.selected_rect_label)
        layout.addWidget(self.view_rect_scene_label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    """
    If you want to start view frome some point at some level, specify <start_level> and <start_image_rect> params. 
    start_image_rect : rect in dimensions of slide at level=start_level. If None - fits the whole size of slide
    """

    def load_slide(self, slide_path, start_level: int = -1, start_image_rect: QRectF = None, preffered_rects_count=2000,
                   zoom_step=1.15):
        self.zoom_step = zoom_step
        # self.slide_path = slide_path
        # self.slide = openslide.OpenSlide(slide_path)
        # self.slide_helper = SlideHelper(self.slide)
        self.slide_helper = SlideHelper(slide_path)

        self.selected_rect_0_level = None

        self.slide_graphics = SlideGraphicsGroup(self.slide_helper.get_slide_path(), preffered_rects_count)
        self.scene.clear()
        self.scene.addItem(self.slide_graphics)

        if start_level == -1 or start_level is None:
            self.current_level = self.slide_helper.get_max_level()
        else:
            self.current_level = start_level
        self.slide_graphics.update_visible_level(self.current_level)
        self.scene.setSceneRect(self.slide_helper.get_rect_for_level(self.current_level))

        def scale_initializer_deffered_function():
            self.view.resetTransform()
            # print("size when loading: ", self.view.viewport().size())
            if start_image_rect:
                self.view.fitInView(start_image_rect, Qt.KeepAspectRatioByExpanding)
                # self.view.fitInView(start_image_rect, Qt.KeepAspectRatio)
                # print("after fit: ", self.current_level, self.get_current_view_scene_rect())
            else:
                start_margins = QMarginsF(200, 200, 200, 200)
                start_image_rect_ = self.slide_helper.get_rect_for_level(self.current_level)
                self.view.fitInView(start_image_rect_ + start_margins, Qt.KeepAspectRatio)

            self.update_labels()

        self.scale_initializer_deffered_function = scale_initializer_deffered_function

    def eventFilter(self, qobj: 'QObject', event: QEvent):
        self.eventSignal.emit(event)
        # print("size when event: ", event, event.type(), self.view.viewport().size())
        if isinstance(event, QPaintEvent):
            """
            we need it deffered because fitInView logic depends on current viewport size. Expecting at this point widget is finally resized before being shown at first
            """
            if self.scale_initializer_deffered_function:
                self.scale_initializer_deffered_function()
                self.scale_initializer_deffered_function = None
        elif isinstance(event, QWheelEvent):
            return self.process_viewport_wheel_event(event)
            # we handle wheel event to prevent GraphicsView interpret it as scrolling
        elif isinstance(event, QMouseEvent):
            return self.process_mouse_event(event)
        return False

    def process_viewport_wheel_event(self, event: QWheelEvent):
        # print("size when wheeling: ", self.view.viewport().size())
        zoom_in = self.zoom_step
        zoom_out = 1 / zoom_in
        zoom_ = zoom_in if event.angleDelta().y() > 0 else zoom_out
        self.update_scale(event.pos(), zoom_)
        event.accept()
        return True

    def process_mouse_event(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            self.update_scale(QPoint(), 1.15)
            # self.take_screenshot()
        elif event.button() == Qt.LeftButton:
            if event.type() == QEvent.MouseButtonPress:
                self.mouse_press_view = QPoint(event.pos())
                self.rubber_band.setGeometry(QRect(self.mouse_press_view, QSize()))
                self.rubber_band.show()
                return True
            elif event.type() == QEvent.MouseButtonRelease:
                self.rubber_band.hide()
                self.remember_selected_rect_params()
                self.slide_graphics.update_selected_rect_0_level(self.selected_rect_0_level)
                self.update_labels()
                self.scene.invalidate()
                return True
        elif event.type() == QEvent.MouseMove:
            self.mouse_pos_scene_label.setText(
                "mouse pos scene: " + point_to_str(self.view.mapToScene(event.pos())))
            if not self.mouse_press_view.isNull():
                self.rubber_band.setGeometry(QRect(self.mouse_press_view, event.pos()).normalized())
            return True

        return False

    def take_screenshot(self):
        scene_rect = self.view.mapToScene(self.view.viewport().rect()).boundingRect()
        image = build_screenshot_image(self.scene, self.view.viewport().size(), scene_rect)
        image.save("view_screenshot_image.png")

    def remember_selected_rect_params(self):
        pos_scene = self.view.mapToScene(self.rubber_band.pos())
        self.rubber_band.size()
        rect_scene = self.view.mapToScene(self.rubber_band.rect()).boundingRect()
        downsample = self.slide_helper.get_downsample_for_level(self.current_level)
        selected_qrectf_0_level = QRectF(pos_scene * downsample,
                                         rect_scene.size() * downsample)
        self.selected_rect_0_level = selected_qrectf_0_level.getRect()

    def update_scale(self, mouse_pos: QPoint, zoom):
        old_mouse_pos_scene = self.view.mapToScene(mouse_pos)
        old_view_scene_rect = self.view.mapToScene(self.view.viewport().rect()).boundingRect()

        old_level = self.get_best_level_for_scale(self.get_current_view_scale())
        old_level_downsample = self.slide_helper.get_downsample_for_level(old_level)
        new_level = self.get_best_level_for_scale(self.get_current_view_scale() * zoom)
        new_level_downsample = self.slide_helper.get_downsample_for_level(new_level)

        level_scale_delta = 1 / (new_level_downsample / old_level_downsample)

        r = old_view_scene_rect.topLeft()
        m = old_mouse_pos_scene
        new_view_scene_rect_top_left = (m - (m - r) / zoom) * level_scale_delta
        new_view_scene_rect = QRectF(new_view_scene_rect_top_left,
                                     old_view_scene_rect.size() * level_scale_delta / zoom)

        new_rect = self.slide_helper.get_rect_for_level(new_level)
        self.scene.setSceneRect(new_rect)

        new_scale = self.get_current_view_scale() * zoom * new_level_downsample / old_level_downsample
        transform = QTransform().scale(new_scale, new_scale).translate(-new_view_scene_rect.x(),
                                                                       -new_view_scene_rect.y())
        self.current_level = new_level
        self.reset_view_transform()
        self.view.setTransform(transform, False)
        self.slide_graphics.update_visible_level(new_level)
        self.update_labels()

    def get_best_level_for_scale(self, scale):
        scene_width = self.scene.sceneRect().size().width()
        candidates = [0]
        for level in self.slide_helper.get_levels():
            w, h = self.slide_helper.get_level_size(level)
            if scene_width * scale <= w:
                candidates.append(level)
        best_level = max(candidates)
        return best_level

    def update_labels(self):
        level_downsample = self.slide_helper.get_downsample_for_level(self.current_level)
        level_size = self.slide_helper.get_level_size(self.current_level)
        self.level_label.setText(
            "current level, downsample, size: {}, {:.4f}, ({}, {})".format(self.current_level, level_downsample,
                                                                           *level_size))
        self.view_rect_scene_label.setText(
            "view_rect_scene: ({:.2f},{:.2f},{:.2f},{:.2f})".format(*self.get_current_view_scene_rect().getRect()))
        if self.selected_rect_0_level:
            self.selected_rect_label.setText(
                "selected rect (0-level): ({:.2f},{:.2f},{:.2f},{:.2f})".format(*self.selected_rect_0_level))

    def reset_view_transform(self):
        self.view.resetTransform()
        self.view.horizontalScrollBar().setValue(0)
        self.view.verticalScrollBar().setValue(0)

    def get_current_view_scene_rect(self):
        return self.view.mapToScene(self.view.viewport().rect()).boundingRect()

    def get_current_view_scale(self):
        scale = self.view.transform().m11()
        return scale
