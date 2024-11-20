# Manim present

This a template for manim-based presentations that is manipulated by a YAML configuration file.
Mainly geared towards AI agents interactions. The outcome is an HTML presentation with metadata
put in a `package.json` file.

> [!NOTE]
> Producing fancy but linear presentations with this tool should be easy and requires no
> Python coding. But this is at very early stages of development, so expect things
> change frequently

[manim-present](https://github.com/FoamScience/manim-present) repository provides an example presentation
to showcase implemented features, but here are some design principles:

1. The presentation flow is **mostly linear**. Often, the last rendered item is used as an anchor
   for the next one.
1. The presentation layout is kept lean and clean; with a title and a logo at the top, and a footer
   that has author, date and a short event description.
1. You can segment the YAML configuration, as long as you include all relevant files in the main one:
   - It's recommended  to configure Title and "Thanks" pages through a `meta/config.yaml`
   - It's also recommended to put default styling values in a `default_styling/config.yaml`
1. The YAML configuration supports python code as values when it makes sense.
   - For example; an angle in radians can be set to `angle: "PI/4"`
   - And there is some special templating for important parameters:
     - `{{ title }}` refers to the slide's title
     - `{{ last }}` refers to last rendered item
     - `{{ small_size }}`, `{{ mid_size }}` and `{{ big_size }}` can be used for font size settings
1. The YAML configuration supports two modes of slide population:
   - `content` through pre-defined steps listed below
   - `hook` which can read custom-made python functions to render Manim objects.
1. If `footer.slide_counter` configuration item is `True`, a slide counter over
   the total count of slides will be displayed. It is recommended to keep this as `False` (default)
   and turn it on as the last iteration on the presentation. If this setting is turned on, there
   will be excessive re-rendering (cached animations get invalidated because the total number of
   slides changes as you add more). It gets increased on each `reset_step`.
1. If you want cite papers, a `references.bib` file must be present at the root folder (where `config.yaml`
   is located)
   - Prefix entry ID with `@@` to cite it.
   - More info about this mechanism in the dedicated section bellow.

## Supplying slide contents

### The content steps

Content slides are composed by steps:
- `code`: rendering code listings, supporting multi-step code reveals through modifications
  to specific code lines.
- `custom`: accepts single-line python manim-like code to produce `Mobjects` to render
- `diagram`: mostly-linear diagramming through rectangle nodes which can be grouped.
- `image`: media rendering for raster image formats; from the images folder.
- `items`: similar to Latex's enumerate, but needs an anchor object for positioning, with
  partial weighting and coloring
- `mathtex`: a Tex environment specifically for math mode. This is similar to `tex`.
- `plot`: simple scatter or line (or both) plotting. CSV files loaded from a `data` folder.
- `reset`: resets the slide, keeping layout elements.
- `svg`: media rendering for SVG objects, recommended for symbols and vector logos.
- `tex`: Latex rendering, recommended only for equations.
- `text`: simple text rendering, controlling font size and text color,
  with partial weighting and coloring
- `video`: renders an MP4 file and can set its playback speed and control its rendered height.
  Video duration is automatically deduced using the `ffmpeg` package. Video files are stored in the
  images folder.

All slide components adhere to a common position scheme (These translate to Manim, in this order):
- `align_to`: to align two objects in a direction. The target object can be the `{{ last }}` rendered item.
- `next_to`: moves the object next to the target, and applies a translation in specified direction
- `shift`: moves the object by the input vector (eg. `2*UP+RIGHT` will move the object by (1, 2) units)
- `rotate`: rotates an object around an axis (Z-axis by default) by an input angle (in radians)

### The hooks system

```yaml
# config.yaml
slides:
  - title: A slide made with a hook function
    number: "1.0"
    hook:
      name: section0 # arbitrary name
      filename: hooks/section0.py # python file that defines example_slide()
      functions: example_slide
```

This configuration will look for `hooks/section0.py` file and load-in the `example_slide` function.
The `example_slide` function should look like:
```python
# hooks/section0.py
SOME_LOCAL_VAR = True
# self: is the presentation class
# cfg: is the hook configuration from config.yaml
# so, cfg.name, cfg.filename, and cfg.functions are reserved
# context: is the local context for the hook function 
def example_slide(self, cfg, context):
    var = context.get("SOME_LOCAL_VAR")
    txt = Text(f"VAR was {var} here")
    self.play(FadeIn(txt, run_time=self.fadein_rt))
    self.next_slide()
```

There are a few important notes for writing hooks:
- You get a Group of objects in `self.layout` including title (index 0), logo, and footer elements
- If you want to remove everything on a slide but keep the layout, call `self.keep_only_objects(self.layout)`
- Don't forget to set the `run_time` property for every animation you construct for a consistent 
  behavior

## Managing Tex-like bibliography

If you want to cite other people's work, you must compile a `references.bib` file that contains
all entries to be cited.

In `text` or `items` elements on the `config.yaml`, you can prefix bibliography entry ID with `@@` to cite it.

For example, if the `references.bib` file has an entry `@misc{authorYear, ...}`, you would use `@@authorYear` 
to cite it. The citation behavior/styling can be configured through:
```yaml
# for example; in default_styling/config.yaml
bibliography:
  style: alpha # style of the bibliography entry in the footer, styles from pybtex python package
  font_size_multiplier: 0.9 # multiplied to get bibliography entry font size relative to very small font size
  line_length: 5 # separation line for bibliography entry. A 0 will omit the separation line
  line_color: "self.main_color" # color of separation line, these can be manim colors, hex colors, or from color presets.
```

You are only allowed to have at-most **two** cited papers per slide "overlay". The first one will be positioned 
on the right, and the second one will be on the left.
