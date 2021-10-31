import io
import urllib

import pandas as pd
import requests
import streamlit as st

from mplsoccer import VerticalPitch


st.set_page_config("Remates | Liga Profesional 2021 | Argentina", layout="wide")

"""
### Remates | Liga Profesional 2021 | Argentina
Todos los remates en el torneo, con la posibilidad de filtrar por distintos criterios

(*por ej. [desde dónde y cuánto le patean a River](), [todos los remates efectuados por Boca en la era Battaglia](), o [cualquier otra combinación]()*).
"""


BASE_URL = st.config.get_option("server.baseUrlPath")

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_URL = st.secrets["GITHUB_URL"]

# some pitch color values
PITCH_COLOR = "white"
PITCH_LINE_COLOR = "darkgrey"
SHOT_OFF_TARGET_COLOR = "lightgrey"
SHOT_ON_TARGET_COLOR = "dimgrey"
SHOT_GOAL_COLOR = "green"
FONT_COLOR = "black"


@st.cache
def load_data():
    """Load shots data from private github repo."""
    headers = {"Authorization": "token {}".format(GITHUB_TOKEN)}
    data = requests.get(GITHUB_URL, headers=headers)
    return pd.read_csv(io.StringIO(data.text))


def render_shots(shots, filters):
    """Render pitch with given shots information."""
    pitch = VerticalPitch(
        pitch_color=PITCH_COLOR,
        line_color=PITCH_LINE_COLOR,
        goal_type="box",
        line_zorder=1,
        linewidth=1,
        half=True,
        pad_bottom=0,
        spot_scale=0,
    )
    fig, axs = pitch.grid(
        figheight=10,
        title_height=0.03,
        endnote_space=0,
        axis=False,
        title_space=0,
        grid_height=0.9,
    )
    fig.set_facecolor(PITCH_COLOR)

    def shot_color(s):
        c = SHOT_OFF_TARGET_COLOR
        if s.is_goal:
            c = SHOT_GOAL_COLOR
        elif s.on_target:
            c = SHOT_ON_TARGET_COLOR
        return c

    if len(shots) > 0:
        pitch.scatter(
            shots.x,
            shots.y,
            s=100 + 850 * shots.xg,
            edgecolors=PITCH_LINE_COLOR,
            c=[shot_color(row) for i, row in shots.iterrows()],
            alpha=0.8,
            marker="o",
            zorder=3,
            ax=axs["pitch"],
        )

        # render median distance line
        median = shots.distance.median()
        pitch.lines(
            120 - median,
            0,
            120 - median,
            80,
            ls="--",
            lw=2,
            color=PITCH_LINE_COLOR,
            alpha=0.8,
            ax=axs["pitch"],
        )

        # legend
        pitch.scatter(
            [123],
            [1],
            s=95,
            color=[SHOT_GOAL_COLOR],
            edgecolors=PITCH_LINE_COLOR,
            alpha=1,
            zorder=2,
            ax=axs["pitch"],
        )
        pitch.annotate(
            "Gol",
            xy=(123, 2),
            c=FONT_COLOR,
            va="center",
            ha="left",
            size=13,
            ax=axs["pitch"],
        )
        pitch.scatter(
            [123],
            [6],
            s=95,
            color=[SHOT_ON_TARGET_COLOR],
            edgecolors=PITCH_LINE_COLOR,
            alpha=1,
            zorder=2,
            ax=axs["pitch"],
        )
        pitch.annotate(
            "Al arco",
            xy=(123, 7),
            c=FONT_COLOR,
            va="center",
            ha="left",
            size=13,
            ax=axs["pitch"],
        )
        pitch.scatter(
            [123],
            [13],
            s=95,
            color=SHOT_OFF_TARGET_COLOR,
            edgecolors=PITCH_LINE_COLOR,
            alpha=1,
            zorder=2,
            ax=axs["pitch"],
        )
        pitch.annotate(
            "Afuera",
            xy=(123, 14),
            c=FONT_COLOR,
            va="center",
            ha="left",
            size=13,
            ax=axs["pitch"],
        )

        pitch.scatter(
            [121, 121, 121],
            [1, 3, 5],
            s=[70, 120, 170],
            color="None",
            edgecolors=PITCH_LINE_COLOR,
            alpha=1,
            zorder=2,
            ax=axs["pitch"],
        )
        pitch.annotate(
            "Calidad de la chance (xG)",
            xy=(121, 6),
            c=FONT_COLOR,
            va="center",
            ha="left",
            size=13,
            ax=axs["pitch"],
        )

        goals = shots[shots["is_goal"]]
        on_target = shots[shots["on_target"]]
        pitch.annotate(
            "{} {}".format(len(goals), "goles" if len(goals) != 1 else "gol"),
            xy=(67, 2),
            c=FONT_COLOR,
            va="center",
            ha="left",
            size=18,
            ax=axs["pitch"],
        )
        if not filters.get("goals_only"):
            # only render this information when all shots are included (to avoid confusion)
            pitch.annotate(
                "{} remates | {} al arco".format(len(shots), len(on_target)),
                xy=(65, 2),
                c=FONT_COLOR,
                va="center",
                ha="left",
                size=15,
                ax=axs["pitch"],
            )
            pitch.annotate(
                "{:.2f} xG | {:.2f} xG/remate".format(
                    sum(shots.xg), sum(shots.xg) / len(shots)
                ),
                xy=(63, 2),
                c=FONT_COLOR,
                va="center",
                ha="left",
                size=15,
                ax=axs["pitch"],
            )

    st.pyplot(fig)


def generate_permalink(widgets):
    """Return link to current filtered shots chart."""
    params = {}
    for k, v in widgets.items():
        if isinstance(v, tuple):
            params[k] = ",".join(map(str, v))
        elif isinstance(v, bool):
            params[k] = int(v)
        else:
            params[k] = v
    qs = urllib.parse.urlencode(params)
    return "{}?{}".format(BASE_URL, qs)


shots = load_data()
max_round = int(shots["round"].max())


filters_def = {
    # name: (widget_type, kwargs, column_name)
    "team": ("selectbox", {"label": "Equipo"}, "team"),
    "rival": ("selectbox", {"label": "Contra"}, "rival"),
    "player": ("selectbox", {"label": "Jugador"}, "player"),
    "rounds": (
        "slider",
        {"label": "Fechas", "min_value": 1, "max_value": max_round},
        "round",
    ),
    "goals_only": ("checkbox", {"label": "Sólo goles"}, "is_goal"),
}


def parse_filters(qs):
    """Parse query string to get filters."""
    filters = {}
    for k, (widget_type, _, _) in filters_def.items():
        v = qs.get(k)
        if v is None:
            continue
        value = v[0]
        if widget_type == "slider":
            filters[k] = tuple(map(int, value.split(",")))
        elif widget_type == "checkbox":
            filters[k] = int(value) == 1
        else:
            filters[k] = value
    return filters


# parse current value for filters from query string
filters = parse_filters(st.experimental_get_query_params())


# render sidebar filters
st.sidebar.write("**Filtros**")

widgets = {}
for filter_key, (widget_type, kwargs, column_name) in filters_def.items():
    # setup widget from params
    widget_func = getattr(st.sidebar, widget_type)
    if widget_type == "selectbox":
        options = [""] + sorted(shots[column_name].unique())
        kwargs["options"] = options
        kwargs["index"] = options.index(filters.get(filter_key, ""))
    elif widget_type == "slider":
        kwargs["value"] = filters.get(
            filter_key, (kwargs["min_value"], kwargs["max_value"])
        )
    elif widget_type == "checkbox":
        kwargs["value"] = filters.get(filter_key, False)
    else:
        raise Exception("unsupported widget")

    # render widget
    widget_value = widget_func(**kwargs)

    # apply dataframe filtering using widget value (chaining filters)
    if widget_type == "selectbox" and widget_value:
        shots = shots[shots[column_name] == widget_value]
    elif widget_type == "slider" and widget_value:
        shots = shots[
            (shots[column_name] >= widget_value[0])
            & (shots[column_name] <= widget_value[1])
        ]
    elif widget_type == "checkbox" and widget_value:
        shots = shots[shots[column_name]]

    # keep value for later reuse
    widgets[filter_key] = widget_value


render_shots(shots, filters=widgets)
permalink = generate_permalink(widgets)
st.markdown("[Link para compartir este gráfico]({})".format(permalink))
