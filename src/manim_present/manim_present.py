#!/usr/bin/env python3
## !! This is a template for scientific presentations using manim
from manim import *
from manim_slides import Slide
from manim.utils import color
import hydra, logging, os, argparse
from omegaconf import DictConfig, OmegaConf
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull
from .CustomMobjects import VideoMobject
import subprocess as sb
import json, ffmpeg
import math, random

__version__ = "0.0.3"
log = logging.getLogger(__name__)

@hydra.main(version_base=None, config_path=os.getcwd(), config_name="config.yaml")
def hydra_main(cfg : DictConfig) -> None:
    log.info("============= Configuration =============")
    log.info(OmegaConf.to_yaml(cfg))
    log.info("=========================================")
    if "version" in cfg.keys() and __version__ != cfg.version:
        log.warning(f"Presentation wants manim-present v{cfg.version} but running with v{__version__}, be careful!")
    scene = YamlPresentation(cfg)
    scene.render()
    populate_package(cfg.meta)
    command="manim-slides convert --to html -c progress=true -c controls=true -cslide_number=true 'YamlPresentation' 'YamlPresentation.html'"
    result = sb.run(command, shell=True, capture_output=True, text=True)
    log.info("============= Manim Slides ==============")
    log.info(result.stdout)
    if result.stderr:
        log.error(result.stderr)

def populate_package(cfg):
    meta = {
        "name": str(cfg.title).lower().replace(" ", "-"),
        "description": cfg.footer.text,
        "author": cfg.author,
        "html-inject-meta": {
          "name": cfg.title,
          "description": cfg.footer.text + ", " + cfg.author + ", " + cfg.time,
          "base_url": cfg.base_url,
          "author": cfg.author,
          "image": f"{cfg.base_url}/thumbnail.png"
        },
    }
    with open("package.json", 'w') as file:
        json.dump(meta, file, indent=4)

class YamlPresentation(Slide):
    def __init__(self, cfg):
        """Register Hydra config to self"""
        super().__init__()
        self.cfg = cfg
        self.layout = Group()
        self.entity_map = {
            "text": self.text_step,
            "tex": self.tex_step,
            "mathtex": self.mathtex_step,
            "code": self.code_step,
            "items": self.items_step,
            "diagram": self.diagram_step,
            "image": self.image_step,
            "svg": self.svg_step,
            "reset": self.reset_step,
            "plot": self.plot_step,
            "video": self.video_step,
            "custom": self.custom_step,
        }
        self.diag_map = {
            "rectangle": self.rectangle_item,
            "group": self.group_diag_items,
        }
        self.hooks = {}

    def register_hook(self, name, func):
        if name not in self.hooks:
            self.hooks[name] = []
        self.hooks[name].append(func)

    def load_hooks(self, cfg):
        if os.path.exists(cfg.filename):
            with open(cfg.filename, 'r') as file:
                c = file.read()
                local_vars = {}
                hook_globals = {
                    '__builtins__': __builtins__,
                }
                hook_globals.update(globals())
                allowed_imports = {
                    'math': math,
                    'random': random,
                    'numpy': np,
                    'pandas': pd,
                }
                hook_globals.update(allowed_imports)
                exec(c, hook_globals, local_vars)
                self.hook_context = local_vars
                for name, func in local_vars.items():
                    if callable(func) and name in cfg.functions:
                        self.register_hook(cfg.name, func)

    def exec_hooks(self, cfg):
        if cfg.name in self.hooks:
            for func in self.hooks[cfg.name]:
                func(self, cfg, self.hook_context)
        else:
            log.warning(f"No hooks registered for {cfg.name}")

    def to_next_slide(self, cfg):
        if "no_next_slide" not in cfg:
            self.next_slide()

    def common_positionning(self, cfg, last):
        if "next_to" in cfg.keys():
            last = last.next_to(self.parse_eval(cfg.next_to.target), self.parse_eval(cfg.next_to.dir))
        if "align_to" in cfg.keys():
            last = last.align_to(self.parse_eval(cfg.align_to.target), self.parse_eval(cfg.align_to.dir))
        if "shift" in cfg.keys():
            last = last.shift(self.parse_eval(cfg.shift))
        if "to_edge" in cfg.keys():
            last = last.to_edge(self.parse_eval(cfg.to_edge))
        if "rotate" in cfg.keys():
            pnt = None if "about_point" not in cfg.rotate.keys() else self.parse_eval(cfg.rotate.about_val)
            axis = OUT if "axis" not in cfg.rotate.keys() else self.parse_eval(cfg.rotate.axis)
            last = last.rotate(self.parse_eval(cfg.rotate.angle), axis=axis, about_point=pnt)
        return last

    def text_step(self, cfg, last):
        t2w = {}
        if "weights" in cfg.keys():
            for e in cfg.weights:
                t2w.update({e.text: self.parse_eval(e.weight)})
        t2c = {}
        if "colors" in cfg.keys():
            for e in cfg.colors:
                t2c.update({e.text: self.parse_eval(e.color)})
        font_size = self.m_size if "font_size" not in cfg.keys() else self.parse_eval(cfg.font_size)
        color = self.text_color if "color" not in cfg.keys() else self.parse_eval(cfg.color)
        last = Text(cfg.text, color=color, t2w=t2w, t2c=t2c, font_size=font_size)
        last = self.common_positionning(cfg, last)
        self.play(FadeIn(last, run_time=self.fadein_rt))
        self.to_next_slide(cfg)
        self.last = last

    def tex_step(self, cfg, last):
        font_size = self.m_size if "font_size" not in cfg.keys() else self.parse_eval(cfg.font_size)
        last = Tex(
            cfg.text,
            tex_environment='center' if "environment" not in cfg.keys() else cfg.environment,
            font_size=font_size
        )
        last = self.common_positionning(cfg, last)
        self.play(FadeIn(last, run_time=self.fadein_rt))
        self.to_next_slide(cfg)
        self.last = last

    def mathtex_step(self, cfg, last):
        font_size = self.m_size if "font_size" not in cfg.keys() else self.parse_eval(cfg.font_size)
        tex_to_color_map = {}
        if "colors" in cfg.keys():
            for e in cfg.colors:
                tex_to_color_map.update({e.text: self.parse_eval(e.color)})
        last = MathTex(
            cfg.text,
            font_size=font_size,
            tex_to_color_map=tex_to_color_map,
        )
        last = self.common_positionning(cfg, last)
        self.play(FadeIn(last, run_time=self.fadein_rt))
        self.to_next_slide(cfg)
        self.last = last

    def image_step(self, cfg, last):
        img = ImageMobject(f"./images/{cfg.image}").scale(float(cfg.scale))
        last = self.common_positionning(cfg, img)
        self.play(FadeIn(last, run_time=self.fadein_rt))
        self.to_next_slide(cfg)
        self.last = last

    def video_step(self, cfg, last):
        probe = ffmpeg.probe(f"./images/{cfg.video}")
        duration = float(probe['format']['duration'])
        speed = 1.0 if "speed" not in cfg.keys() else float(cfg.speed)
        video = VideoMobject(f"./images/{cfg.video}", speed=speed).scale_to_fit_height(cfg.height)
        video = self.common_positionning(cfg, video)
        self.add(video)
        self.wait(duration)
        self.to_next_slide(cfg)
        self.last = video

    def svg_step(self, cfg, last):
        color = None if "color" not in cfg.keys() else self.parse_eval(cfg.color)
        fill_color = color if "fill_color" not in cfg.keys() else self.parse_eval(cfg.fill_color)
        stroke_color = color if "stroke_color" not in cfg.keys() else self.parse_eval(cfg.stroke_color)
        img = SVGMobject(
            f"./images/{cfg.image}",
            height=cfg.height,
            color=color,
            stroke_color=stroke_color,
            fill_color=fill_color
        )
        last = self.common_positionning(cfg, img)
        self.play(FadeIn(last, run_time=self.fadein_rt))
        self.to_next_slide(cfg)
        self.last = last

    def code_step(self, cfg, last):
        line_nbrs = True if "line_numbers" not in cfg.keys() else cfg.line_numbers
        line_nbr_from = 1 if "line_number_from" not in cfg.keys() else cfg.line_number_from
        background = "window" if "background" not in cfg.keys() else cfg.background
        if "steps" in cfg.keys():
            mod_counter = 0
            last_code = None
            for e in cfg.steps:
                if "modification" in e.keys():
                    code_partial = cfg.code
                    for m in e.modification:
                        for mi in m:
                            code_partial = self.replace_nth_line(code_partial, mi, m[mi])
                    last = Code(
                        code=code_partial,
                        language=cfg.language,
                        insert_line_no=line_nbrs,
                        line_no_from=line_nbr_from,
                        background=background,
                    )
                    last = self.common_positionning(cfg, last)
                    if mod_counter > 0:
                        self.play(Transform(last_code, last, run_time=self.transform_rt))
                    else:
                        self.play(FadeIn(last, run_time=self.fadein_rt))
                        self.last = last
                    last_code = last
                    mod_counter += 1
                    self.to_next_slide(cfg)
                else:
                    self.entity_map[e.type](e, last)
            last = Code(
                code=cfg.code,
                language=cfg.language,
                insert_line_no=line_nbrs,
                line_no_from=line_nbr_from,
                background=background,
            )
            last = self.common_positionning(cfg, last)
            self.play(Transform(last_code, last, run_time=self.transform_rt))
        else:
            last = Code(
                code=cfg.code,
                language=cfg.language,
                insert_line_no=line_nbrs,
                line_no_from=line_nbr_from,
                background=background,
            )
            last = self.common_positionning(cfg, last)
            self.play(FadeIn(last, run_time=self.fadein_rt))
        self.to_next_slide(cfg)
        self.last = last

    def custom_step(self, cfg, last):
        new = self.parse_eval(cfg.custom)
        last = self.common_positionning(cfg, new)
        self.play(FadeIn(last, run_time=self.fadein_rt))
        self.to_next_slide(cfg)
        self.last = last

    def items_step(self, cfg, last):
        distance = self.item_distance if "distance" not in cfg.keys() else float(cfg.distance)
        anchor = last if "anchor" not in cfg.keys() else self.parse_eval(cfg.anchor)
        t2w = {} if "weights" not in cfg.keys() else {item['text']: self.parse_eval(item['weight']) for item in cfg.weights}
        t2c = {} if "colors" not in cfg.keys() else {item['text']: self.parse_eval(item['color']) for item in cfg.colors}
        last = self.itemize(cfg.bullets, anchor, distance, FadeIn, t2w=t2w, t2c=t2c)
        self.to_next_slide(cfg)
        self.last = last

    def reset_step(self, cfg, last):
        self.keep_only_objects(self.layout)
        self.next_slide()
        self.last = self.layout[0]

    def plot_step(self, cfg, last):
        """NOT USABLE YET"""
        df = pd.read_csv(f"./data/{cfg.csv_file}")
        y_range = [1e100, -1e100] if "y_range" not in cfg.keys() else cfg.y_range
        for col in cfg["columns"][1:]:
            ymin = df[col].min()
            ymax = df[col].max()
            if y_range[0] > ymin:
                y_range[0] = ymin
            if y_range[1] < ymax:
                y_range[1] = ymax
        x_range = [1e100, -1e100] if "x_range" not in cfg.keys() else cfg.x_range
        xmin = df[cfg["columns"][0]].min()
        xmax = df[cfg["columns"][0]].max()
        if x_range[0] > ymin:
            x_range[0] = ymin
        if x_range[1] < ymax:
            x_range[1] = ymax
        axes_color = WHITE if "axes_color" not in cfg.keys() else self.parse_eval(cfg.axes_color)
        x_length = 6 if "x_length" not in cfg.keys() else int(cfg.x_length)
        y_length = 6 if "y_length" not in cfg.keys() else int(cfg.y_length)
        x_steps = (df[cfg["columns"][0]].max()-df[cfg["columns"][0]].min())//x_length  if "x_step" not in cfg.keys() else cfg.x_step
        y_steps = (y_range[1]-y_range[0])/y_length if "y_step" not in cfg.keys() else cfg.y_step
        axes = Axes(
            x_range=[x_range[0], x_range[1], x_steps],
            y_range=[y_range[0], y_range[1], y_steps],
            x_length=x_length,
            y_length=y_length,
            axis_config={"color": axes_color},
            tips=False,
        ).add_coordinates()
        x_label = Text(cfg["columns"][0], color=axes_color).move_to(axes.x_axis.get_center()+0.7*DOWN)
        for tick_label in axes.x_axis.numbers:
            tick_label.set_color(axes_color)
            tick_label.scale(0.7)
            tick_label.set(font=self.t_family)
        for tick_label in axes.y_axis.numbers:
            tick_label.set_color(axes_color)
            tick_label.scale(0.7)
            tick_label.set(font=self.t_family)
        plt = VGroup(axes, x_label)
        if "y_axis_label" in cfg.keys():
            y_axis_label = Text(cfg.y_axis_label, color=axes_color).move_to(axes.y_axis.get_end()+0.5*UP)
            plt.add(y_axis_label)
        else:
            plt.add(Text(""))
        for col in cfg["columns"][1:]:
            dots = VGroup(*[
                Dot(axes.coords_to_point(x, y), color=self.parse_eval(cfg.colors[col]))
                for x, y in zip(df[cfg["columns"][0]], df[col])
            ])
            line_graph = axes.plot_line_graph(
                x_values=df[cfg["columns"][0]],
                y_values=df[col],
                line_color=self.parse_eval(cfg.colors[col]),
                add_vertex_dots=False,
                vertex_dot_style={'color': self.parse_eval(cfg.colors[col])}
            )
            y_label = axes.get_y_axis_label( Text(col, color=self.parse_eval(cfg.colors[col])) ).next_to(line_graph, RIGHT)
            if "labels" in cfg.keys():
                if col in cfg["labels"].keys():
                    y_label = self.common_positionning(cfg.labels[col], y_label)
            plt.add(y_label)
            if "scatter" in cfg["kind"] and "noscatter" not in cfg["kind"]:
                plt.add(dots)
            if "line" in cfg["kind"] and "noline" not in cfg["kind"]:
                plt.add(line_graph)
            if "fit" in cfg["kind"] and "nofit" not in cfg["kind"]:
                pass
        last = self.common_positionning(cfg, plt)
        n_init = 3
        self.play(FadeIn(last[0:n_init], run_time=self.fadein_rt))
        self.to_next_slide(cfg)
        for i in range(len(cfg["columns"][1:])):
            self.to_next_slide(cfg)
            start = n_init+i*(len(last[n_init:]) // len(cfg["columns"][1:]))
            end = start + len(last[n_init:]) // len(cfg["columns"][1:])
            self.play(DrawBorderThenFill(last[start:end], run_time=self.drawborderthenfill_rt))
        self.to_next_slide(cfg)
        self.last = last


    def rectangle_item(self, cfg, last):
        prev = self.last.copy()
        font_size = self.m_size if "font_size" not in cfg.keys() else self.parse_eval(cfg.font_size)
        txt = Text(cfg.text, font_size=font_size)
        color = self.main_color if "color" not in cfg.keys() else self.parse_eval(cfg.color)
        opacity = self.opacity if "opacity" not in cfg.keys() else float(cfg.opacity)
        b = SurroundingRectangle(txt, color=color, buff=self.box_buff)
        bg = BackgroundRectangle(txt, color=color, fill_opacity=opacity, buff=self.box_buff)
        grp = VGroup(txt, b, bg)
        last = self.common_positionning(cfg, grp)
        self.last = last
        self.draw_arrow_to_last(cfg, prev)
        self.play(FadeIn(last, run_time=self.fadein_rt))
        self.to_next_slide(cfg)
        return { "anchors": bg.get_anchors(), "type": "rectangle" }

    def draw_arrow_to_last(self, cfg, prev):
        def get_pos(obj):
            if isinstance(obj, VGroup) or isinstance(obj, Group):
                return get_pos(obj[-1])
            return np.array([obj.get_top(), obj.get_bottom(), obj.get_right(), obj.get_left(), *obj.get_anchors()])
        if "arrow_from" in cfg.keys():
            prev_coords = get_pos(prev)
            last_coords = get_pos(self.last)
            color = None
            if "arrow_color" in cfg.keys():
                color = self.parse_eval(cfg.arrow_color)
            else:
                if isinstance(prev, Group) or isinstance(prev, VGroup):
                    color = prev[1].get_color()
                else:
                    color = prev.get_color()
            c1 = prev.get_center()
            c2 = self.last.get_center()
            same_x = np.isclose(c1[0], c2[0])
            same_y = np.isclose(c1[1], c2[1])
            dx1 = np.linalg.norm(prev_coords - c2, axis=1)
            dx2 = np.linalg.norm(last_coords - c1, axis=1)
            a1 = prev_coords[np.argmin(dx1)]
            a2 = last_coords[np.argmin(dx2)]
            angle = np.arctan2(a2[1] - a1[1], a2[0] - a1[0])
            if same_x or same_y or np.abs(angle) < TAU/10 or np.abs(np.abs(angle)-TAU/4) < TAU/10 :
                self.play(FadeIn(Arrow(a1, a2, buff=0.1, color=color), run_time=self.fadein_rt))
            else:
                self.play(FadeIn(CurvedArrow(a1, a2, color=color, angle=angle), run_time=self.fadein_rt))
    
    def group_diag_items(self, cfg, last):
        def get_furthest_from(pts, centroid):
            dx = np.linalg.norm(pts - centroid, axis=1)
            np.max(dx)
            max_idx = np.where(dx == np.max(dx))[0]
            return [pts[idx] for idx in max_idx]
        group_elements = Group()
        anchors = []
        anchor_points = []
        for e in cfg.steps:
            subanchors = self.diag_map[e.type](e, last)
            group_elements.add(self.last)
            anchors.append(subanchors)
            anchor_points.append(subanchors["anchors"])
        group_color = self.warn_color if "color" not in cfg.keys() else self.parse_eval(cfg.color)
        points = np.vstack(anchor_points)
        points = np.unique(points, axis=0)
        centroid = np.mean(points, axis=0)

        selected_points = []
        for anch in anchors:
            if anch["type"] != "group":
                selected_points += get_furthest_from(anch["anchors"], centroid)
            else:
                selected_points += list(anch["anchors"])
        selected_points = np.vstack(selected_points)
        selected_points = np.unique(selected_points, axis=0)
        selected_points += 1e-2 * np.random.randn(*selected_points.shape)

        opacity = self.opacity if "opacity" not in cfg.keys() else float(cfg.opacity)
        padded_hull_points = []
        if (len(selected_points) > 3):
            hull = ConvexHull(selected_points)
            array_set = set(tuple(arr.tolist()) for arr in selected_points[hull.vertices])
            hull_points = [np.array(tpl) for tpl in array_set]
            padding_factor = 1.1 if "padding" not in cfg.keys() else float(cfg.padding)
            for point in hull_points:
                direction = point - centroid
                padded_point = centroid + padding_factor * direction
                padded_hull_points.append(padded_point)
            padded_hull_points = np.array(padded_hull_points)
        else:
            padded_hull_points = selected_points
        def angle_from_centroid(point):
            return np.arctan2(point[1] - centroid[1], point[0] - centroid[0])
        hull_points_sorted = sorted(padded_hull_points, key=angle_from_centroid)
        curved_surface = VMobject()
        if "kind" in cfg.keys() and cfg["kind"] == "rectangle":
            curved_surface = SurroundingRectangle(Polygon(*hull_points_sorted))
        else:
            curved_surface.set_points_smoothly([*hull_points_sorted, hull_points_sorted[0]])
        curved_surface.set_fill(group_color, opacity=opacity)
        curved_surface.set_stroke(group_color, width=0)
        self.play(FadeIn(curved_surface, run_time=self.fadein_rt))
        group_elements.add(curved_surface)
        self.text_step(cfg.label, group_elements)
        if "last_is_group" in cfg.keys() and bool(cfg.last_is_group):
            self.last = group_elements
        else:
            self.last = group_elements[-1]
        self.to_next_slide(cfg)
        return { "anchors": selected_points, "type": "group" }

    def diagram_step(self, cfg, last):
        for e in cfg.steps:
            self.diag_map[e.type](e, last)

    def parse_eval(self, content):
        content = content.replace("{{ title }}", "self.layout[0]")
        content = content.replace("{{ last }}", "self.last")
        content = content.replace("{{ small_size }}", "self.s_size")
        content = content.replace("{{ mid_size }}", "self.m_size")
        content = content.replace("{{ big_size }}", "self.b_size")
        return eval(content)

    def set_defaults(self):
        """Set style defaults"""
        def parse_or_default(lvl0, lvl1, default_value, eval=True):
            if not eval:
                return default_value if lvl0 not in c.keys() or lvl1 not in c[lvl0].keys() else c[lvl0][lvl1]
            if lvl0 in c.keys() and lvl1 in c[lvl0].keys():
                if str(c[lvl0][lvl1]).startswith("#"):
                    return c[lvl0][lvl1]
            return default_value if lvl0 not in c.keys() or lvl1 not in c[lvl0].keys() else self.parse_eval(c[lvl0][lvl1])
        c = self.cfg.default_styling
        self.main_color = parse_or_default("color_presets", "main", color.TEAL_A)
        self.bg_color = parse_or_default("color_presets", "bg", color.GRAY_E)
        self.secondary_color = parse_or_default("color_presets", "secondary", color.BLUE_B)
        self.warn_color = parse_or_default("color_presets", "warn", color.YELLOW_C)
        self.important_color = parse_or_default("color_presets", "important", color.RED_C)
        self.opacity = parse_or_default("color_presets", "opacity", 0.3, False)
        self.text_color = parse_or_default("color_presets", "text", color.WHITE)
        self.item_icon = parse_or_default("itemize", "icon", "•", False)
        self.item_distance = parse_or_default("itemize", "distance", 1.5, False)
        self.box_buff = parse_or_default("diagram", "buff", 0.1, False)
        self.vs_size = parse_or_default("font", "very_small", 12, False)
        self.s_size = parse_or_default("font", "small", 16, False)
        self.m_size = parse_or_default("font", "mid", 20, False)
        self.b_size = parse_or_default("font", "big", 25, False)
        self.t_family = parse_or_default("font", "family", "Comic Code Ligatures", False)
        self.camera.frame_rate = parse_or_default("camera", "frame_rate", 60, False)
        self.itemize_rt = parse_or_default("runtime", "Itemize", 0.5, False)
        self.fadein_rt = parse_or_default("runtime", "FadeIn", 0.5, False)
        self.fadeout_rt = parse_or_default("runtime", "FadeOut", 0.5, False)
        self.transform_rt = parse_or_default("runtime", "Transform", 0.5, False)
        self.drawborderthenfill_rt = parse_or_default("runtime", "DrawBorderThenFill", 0.5, False)
        Text.set_default(
            font=self.t_family,
            color=self.text_color,
            font_size=self.s_size
        )
        Code.set_default(
            font=self.t_family,
            font_size=self.s_size,
            style="manni",
            background="window",
            tab_width=4,
            line_spacing=0.65
        )
        Tex.set_default(
            color=self.text_color,
            font_size=self.m_size
        )

    def title_page(self):
        """Layout of title page"""
        self.layout = Group()
        if not isinstance(self.cfg.meta.title, str):
            raise Exception("Title in meta configuration is empty or not a string")
        title = Text(self.cfg.meta.title, font_size=self.b_size)
        footer_t2w = {}
        if "bold" in self.cfg.meta.footer.keys():
            footer_t2w = {it: BOLD for it in self.cfg.meta.footer.bold}
        footer = Text(self.cfg.meta.footer.text, t2w=footer_t2w, font_size=self.vs_size).to_edge(DOWN+RIGHT)
        author = Text(f"{self.cfg.meta.author}, {self.cfg.meta.time}", font_size=self.vs_size).to_edge(DOWN+LEFT)
        logo = ImageMobject(f"./images/{self.cfg.meta.logo.image}").next_to(title, UP).scale(self.cfg.meta.logo.scale)
        self.layout.add(title, footer, author, logo)
        self.play(FadeIn(self.layout))

    def thanks_page(self):
        """Layout of thanks page"""
        if not isinstance(self.cfg.meta.thanks, str):
            raise Exception("Thanks in meta configuration is empty or not a string")
        self.keep_only_objects(self.layout)
        thanks = Text(self.cfg.meta.thanks, font_size=self.b_size+5)
        self.play(Transform(self.layout[0], thanks, run_time=self.transform_rt))

    def replace_nth_line(self, string, n, repl):
        """replace nth line of string with repl"""
        lines = string.splitlines()
        if 0 <= n-1 < len(lines):
            lines[n-1] = repl
        return "\n".join(lines)

    def keep_only_objects(self, *objs):
        """reset slides but keep passed-in objects"""
        self.clear()
        self.add(*objs)

    def itemize(self, items, anchor, distance, animation, **kwargs):
        anims = []
        mobjs = []
        mark_item_b = {f"{i+1}{self.item_icon}":BOLD for i in range(len(items))}
        if 't2w' in kwargs and isinstance(kwargs['t2w'], dict):
            origt2w = kwargs.pop('t2w', None)
            mark_item_b.update(origt2w)
        mark_item_c = {f"{i+1}{self.item_icon}":self.main_color for i in range(len(items))}
        if 't2c' in kwargs and isinstance(kwargs['t2c'], dict):
            origt2c = kwargs.pop('t2c', None)
            mark_item_c.update(origt2c)
        for i in range(len(items)):
            mobjs.append(Text(
                f"{i+1}{self.item_icon} {items[i]}",
                font_size=self.s_size,
                t2w=mark_item_b,
                t2c=mark_item_c,
                **kwargs))
            if i == 0:
                mobjs[i].next_to(anchor, DOWN*distance).align_to(anchor, LEFT)
            else:
                mobjs[i].next_to(mobjs[i-1], DOWN).align_to(mobjs[i-1], LEFT)
        anims = [animation(mobjs[i], run_time=self.itemize_rt) for i in range(len(items))]
        self.play(AnimationGroup(*anims))
        return mobjs[-1]

    def header(self, header, number):
        return Text(f"{number} {header}", t2w={f"{number}": BOLD}, font_size=self.b_size).to_edge(UP+LEFT)
    
    def first_yaml_slide(self, cfg, logo_scale):
        self.play(
            Transform(self.layout[0], self.layout[0].copy().to_edge(UP+LEFT), run_time=self.transform_rt),
            Transform(self.layout[-1], self.layout[-1].copy().scale(logo_scale).to_edge(UP+RIGHT), run_time=self.transform_rt),
        )
        self.yaml_slide(cfg)

    def yaml_slide(self, cfg):
        title = self.header(cfg.title, cfg.number)
        self.play(Transform( self.layout[0], title , run_time=self.transform_rt))
        self.last = self.layout[0]
        if "content" in cfg.keys():
            for idx in range(len(cfg.content)):
                c = cfg.content[idx]
                self.entity_map[c.type](c, self.last)
        elif "hook" in cfg.keys():
            self.load_hooks(cfg.hook)
            self.exec_hooks(cfg.hook)
        else:
            raise Exception("Either 'content' or 'hook' need to be present in slide configuration")

    def construct(self):
        self.set_defaults()
        self.camera.background_color = self.bg_color
        ## Title page
        self.title_page()
        self.next_slide()
        for idx in range(len(self.cfg.slides)):
            self.keep_only_objects(self.layout)
            self.last = self.layout[0]
            sl = self.cfg.slides[idx]
            if idx == 0:
                self.first_yaml_slide(sl, 0.5)
            else:
                self.yaml_slide(sl)
            self.next_slide()
        self.thanks_page()

def main():
    parser = argparse.ArgumentParser(
        description="Manim-Present",
        epilog="Further arguments can be passed to Hydra.\nExample: `manim-present +setting=3` will add setting to the configuration."
    )
    parser.add_argument("--version", action="version", version=__version__)
    args, unknown = parser.parse_known_args()
    hydra_main()

if __name__ == "__main__":
    main()
