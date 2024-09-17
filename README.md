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
   that has author, date and the event description.
1. You can segment the YAML configuration, as long as you include all relevant files in the main one:
   - It's recommended  to configure Title and Thanks pages through a `meta/config.yaml`
   - It's also recommended to put default styling values in a `default_styling/config.yaml`
1. The YAML configuration supports python code as values when it makes sense.
   - For example; an angle in radians can be set to `angle: "PI/4"`
   - And there is some special templating for important parameters:
     - `{{ title }}` refers to the slide's title
     - `{{ last }}` refers to last rendered item
     - `{{ small_size }}`, `{{ mid_size }}` and `{{ big_size }}` can be used for font size settings
1. Slides are composed by steps:
   - `code`: rendering code listings, supporting multi-step code reveals through modifications
     to specific code lines.
   - `custom`: accepts single-line python manim-like code to produce `Mobjects` to render
   - `diagram`: mostly-linear diagramming through rectangle nodes which can be grouped.
   - `image`: media rendering for raster image formats; from the images folder.
   - `items`: similar to Latex's enumerate, but needs an anchor object for positioning, with
     partial weighting and coloring
   - `plot`: simple scatter or line (or both) plotting. CSV files loaded from a `data` folder.
   - `reset`: resets the slide, keeping layout elements.
   - `svg`: media rendering for SVG objects, recommended for symbols and vector logos.
   - `tex`: Latex rendering, recommended only for equations.
   - `text`: simple text rendering, controlling font size and text color,
     with partial weighting and coloring
   - `video`: renders an MP4 file and can set its playback speed and control its rendered height.
     Video duration is automatically deduced using the `ffmpeg` package. Video files are stored in the
     images folder.
1. All slide components adhere to a common position scheme (These translate to Manim, in this order):
   - `align_to`: to align two objects in a direction. The target object can be the `{{ last }}` rendered item.
   - `next_to`: moves the object next to the target, and applies a translation in specified direction
   - `shift`: moves the object by the input vector (eg. `2*UP+RIGHT` will move the object by (1, 2) units)
   - `rotate`: rotates an object around an axis (Z-axis by default) by an input angle (in radians)
