import marimo

__generated_with = "0.13.15"
app = marimo.App(width="medium", app_title="Strava Activity Analyzer")


@app.cell
def _(mo):
    mo.md(
        r"""
    # Strava Activity Analyzer 🏃‍♀️‍➡️​🏃‍➡️​!

    Visualize your progress 📈 and get insights on your activities 📋!

    ➡️ This application is powered by [`marimo`](https://github.com/marimo-team/marimo), [`strava-client`](https://github.com/GiovanniGiacometti/strava-client), [`polars`](https://pola.rs/), [`altair`](https://altair-viz.github.io/index.html) and [`plotly`](https://plotly.com/).

    ➡️ The authentication process is detailed [here](https://github.com/GiovanniGiacometti/strava-client?tab=readme-ov-file#authentication).

    ➡️ Code is available [here](https://github.com/GiovanniGiacometti/strava-marimo-analyzer).

    ---
    """
    )
    return


@app.cell
def _(mo):
    md_initial = mo.md("""Fill in the required information to power up your personal dashboard! 🔥

        For more details on each field, check out the [strava-client documentation](https://github.com/GiovanniGiacometti/strava-client).

        > All data stays entirely in your browser and is never shared.

        **Note**: You must already have obtained the information below by creating a Strava application and authorizing it to access your data. You can find detailed information on the process in the library documentation linked above.

        {use_mocked_data}

        {client_id}

        {client_secret}

        {access_token}

        {refresh_token}

        """)
    return (md_initial,)


@app.cell
def _(md_initial, mo, sys, use_mocked_data, validate_form):
    can_instantiate_client = False
    local = False

    # NOT running in wasm, see https://github.com/marimo-team/marimo/issues/3194#issuecomment-2557397627
    if "pyodide" in sys.modules:
        # We assume information are given through a .env file or through the default
        # settings file
        can_instantiate_client = True
        local = True
        starting_form = None

    else:
        # We ask the credentials, put them into a StravaSettings object and create the client
        # accordingly

        can_instantiate_client = True
        local = False

        client_id_text = mo.ui.text(
            placeholder="Client ID...", label="Client ID", full_width=True
        )
        client_secret_text = mo.ui.text(
            placeholder="Client Secret...", label="Client Secret", full_width=True
        )
        access_token_text = mo.ui.text(
            placeholder="Access Token...", label="Access Token", full_width=True
        )
        refresh_token_text = mo.ui.text(
            placeholder="Refresh Token...",
            label="Refresh Token",
            full_width=True,
        )

        starting_form = md_initial.batch(
            client_id=client_id_text,
            client_secret=client_secret_text,
            access_token=access_token_text,
            refresh_token=refresh_token_text,
            use_mocked_data=use_mocked_data,
        ).form(validate=validate_form)

    starting_form
    return can_instantiate_client, local, starting_form


@app.cell
def _(datetime, strava_client):
    def sanitize_form(form_value) -> dict[str | None, str | None]:
        # insert a fake expires at so that the client refreshes the token
        form_value["expires_at"] = int(
            (datetime.datetime.now() - datetime.timedelta(hours=1)).timestamp()
        )

        form_value.remove("use_mocked_data")

        return form_value

    def validate_form(form_value) -> str | None:
        if form_value["use_mocked_data"]:
            return

        errors = []

        for key, value in form_value.items():
            if not value or value == "":
                errors.append(f"{' '.join(key.split('_'))} is required")

        if errors:
            return ", ".join(errors)

        try:
            strava_client.models.settings.StravaSettings.model_validate(
                sanitize_form(form_value)
            )
        except Exception as e:
            return str(e)

    return sanitize_form, validate_form


@app.cell
async def _(
    can_instantiate_client,
    local,
    mo,
    s_client,
    sanitize_form,
    starting_form,
    strava_client,
):
    mo.stop(not can_instantiate_client)

    scopes = [
        strava_client.enums.auth.StravaScope.READ,
        strava_client.enums.auth.StravaScope.ACTIVITY_READ,
        strava_client.enums.auth.StravaScope.ACTIVITY_READ_ALL,
    ]

    _call = None

    client_ready = False
    load_mocked_activities = False

    if local:
        client = s_client.StravaClient(scopes=scopes)
        client_ready = True

    else:
        mo.stop(starting_form.value is None)
        import asyncio

        with mo.status.spinner(title="Loading...") as _spinner:
            if starting_form.value.get("use_mocked_data", False):
                load_mocked_activities = True

            else:
                _spinner.update("Instantiating client..")

                await asyncio.sleep(0.1)

                settings = strava_client.models.settings.StravaSettings.model_validate(
                    sanitize_form(starting_form.value)
                )
                client = s_client.StravaClient(
                    scopes=scopes, settings=settings, dump_settings=False
                )

                # Make a call to understand if values are correct
                try:
                    client.get_activities(page=1, per_page=1)
                    _spinner.update("Done!")
                    client_ready = True
                except Exception as e:
                    _call = mo.callout(
                        f"""Something is wrong. Please check the information provided. 

                    Exception: {e}""",
                        kind="danger",
                    )

    _call
    return client, client_ready, load_mocked_activities


@app.cell(hide_code=True)
def _(end_date, filtered_df, heatmap_chart, mo, start_date):
    _range = mo.md(
        f"""
        Select a time range to filter activities. The dashboard will update automatically 😉.

        {start_date} - {end_date}
        """
    )

    # Define heatmap here as it can't be where its value is used
    heatmap_selection = heatmap_chart(filtered_df)

    _range
    return (heatmap_selection,)


@app.cell
def _(
    filtered_df,
    get_average_column,
    get_average_speed,
    get_column_sum,
    get_nice_duration,
    heatmap_selection,
    mo,
    pl,
):
    _selected_activities = heatmap_selection.value

    # If nothing was selected, we use all data
    if (_selected_activities := heatmap_selection.value).height == 0:
        displayed_activities = filtered_df
    else:
        # We might have more than one activity for each block
        # hence we explode on ids to have a row for each activity
        _exploded_activities = _selected_activities.explode("id")

        displayed_activities = filtered_df.join(_exploded_activities, on="id")

    displayed_activities = displayed_activities.with_columns(
        start_date_str=pl.col("start_date").dt.strftime("%Y/%m/%d %H:%M:%S")
    )

    n_activities = len(displayed_activities)

    n_activities_stat = mo.stat(
        label="Number of activities",
        bordered=True,
        value=f"{n_activities}",
    )

    total_kms_stat = mo.stat(
        label="Total Kilometers",
        bordered=True,
        value=f"{get_column_sum(displayed_activities, 'kms'):.0f}",
    )

    average_kms_stat = mo.stat(
        label="Average Distance" if n_activities > 1 else "Distance",
        bordered=True,
        value=f"{get_average_column(displayed_activities, 'kms'):.2f}",
    )

    average_run_duration = mo.stat(
        label="Average Duration" if n_activities > 1 else "Duration",
        bordered=True,
        value=f"{get_nice_duration(get_average_column(displayed_activities, 'elapsed_time'))}",
    )

    average_speed = mo.stat(
        label="Average Speed (min / km)" if n_activities > 1 else "Speed (min/km)",
        bordered=True,
        value=f"{get_average_speed(displayed_activities)}",
    )

    mo.vstack(
        [
            mo.hstack(
                [
                    n_activities_stat,
                    total_kms_stat,
                    average_kms_stat,
                    average_run_duration,
                    average_speed,
                ],
                widths="equal",
                gap=1,
            ),
            heatmap_selection,
        ]
    )
    return (displayed_activities,)


@app.cell
def _(
    activity_focus,
    bar_chart_distance,
    bar_chart_speed,
    displayed_activities,
    mo,
):
    mo.vstack(
        [
            mo.md("""Click on individual cells of the heatmap or click and drag to select multiple cells at once. 👆

        The plots below will automatically update to include only the selected activities!

        Available plots 👇

        ⏩ **Activity Focus**: explore the speed progression of your selected activities. Compare multiple ones side by side|
    
        📊 **Speed**: see how your activity speeds are distributed.

        📏 **Distance**: view the distance distribution across your selected activities.


        """),
            mo.ui.tabs(
                {
                    "::lucide:focus:: Activity Focus": activity_focus(),
                    "::lucide:wind:: Speed": bar_chart_speed(_df=displayed_activities),
                    "::lucide:land-plot:: Distance": bar_chart_distance(
                        _df=displayed_activities,
                    ),
                }
            ),
        ]
    )
    return


@app.cell
def _(
    displayed_activities,
    dropdown_activities,
    fetch_activity_stream,
    fetch_mocked_activity_stream,
    get_mt_km_speed,
    get_mt_km_speed_float,
    load_mocked_activities,
    mo,
    np,
    pl,
    plotly,
    px,
    strava_client,
):
    def activity_focus():
        if not dropdown_activities.value:
            return mo.vstack(
                [
                    dropdown_activities,
                    mo.callout("Select at least one activity!"),
                ]
            )

        fig = plotly.graph_objects.Figure()

        selected_activities = displayed_activities.filter(
            pl.col("start_date_str").is_in(dropdown_activities.value)
        )

        min_velocity = None
        max_velocity = None

        # preload mocked activites
        if load_mocked_activities:
            mocked_streams = fetch_mocked_activity_stream()

        for i, _id in enumerate(selected_activities["id"].to_list()):
            if load_mocked_activities:
                # a bit of an hack, data is not structured in the best way possible unfortunately
                stream = (
                    strava_client.models.api.StravaActivityStream.model_validate_json(
                        list(
                            next(
                                stream
                                for stream in mocked_streams
                                if int(list(stream.keys())[0]) == _id
                            ).values()
                        )[0]
                    )
                )
            else:
                stream = fetch_activity_stream(
                    activity_id=_id, keys=["velocity_smooth"]
                )

            # Sample every 3rd point to increase smoothness
            df = pl.DataFrame(
                {
                    "Distance": list(
                        map(lambda x: round(x / 1000, 2), stream.distance.data[::3])
                    ),
                    "Velocity (minkm)": list(
                        map(get_mt_km_speed, stream.velocity_smooth.data[::3])
                    ),
                    "Velocity": stream.velocity_smooth.data[::3],
                }
            )

            # Filter out unreal Velocity values
            df = df.filter(pl.col("Velocity") >= 1.0)

            min_velocity = (
                df["Velocity"].min()
                if not min_velocity
                else min(min_velocity, df["Velocity"].min())
            )
            max_velocity = (
                df["Velocity"].max()
                if not max_velocity
                else max(max_velocity, df["Velocity"].max())
            )

            activity_date = selected_activities.filter(pl.col("id") == _id)[
                "start_date_str"
            ].item()

            fig.add_trace(
                plotly.graph_objects.Scatter(
                    x=df["Distance"],
                    y=df["Velocity"],
                    mode="lines",
                    marker=dict(
                        color=px.colors.qualitative.Dark24[
                            i % len(px.colors.qualitative.Dark24)
                        ]
                    ),
                    name=activity_date,
                    hovertemplate=(
                        "<b>%{meta}</b><br><br>"
                        + "<b>Distance:</b> %{x:.2f} km<br>"
                        + "<b>Speed:</b> %{customdata} min/km<br>"
                        + "<extra></extra>"
                    ),
                    customdata=df["Velocity (minkm)"],
                    meta=activity_date,
                )
            )

        fig.update_layout(
            title={
                "text": "Speed",
                "font": {"size": 24},
                "x": 0.5,
                "xanchor": "center",
            },
            xaxis_title={"text": "Distance (km)", "font": {"size": 18}},
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend={
                "bgcolor": "rgba(255,255,255,0.5)",
                "bordercolor": "rgba(200,200,200,0.5)",
                "borderwidth": 1,
                "font": {"size": 12},
                "orientation": "v",
                "yanchor": "middle",
                "y": 0.5,
                "xanchor": "left",
                "x": 1.01,
            },
            font={"family": "Arial"},
            hovermode="closest",
        )

        # Add grid lines but make them light
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(200,200,200,0.2)",
            zeroline=False,
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(200,200,200,0.2)",
            zeroline=False,
        )

        # Create custom tick positions and labels
        velocity_ticks = np.arange(int(min_velocity), int(max_velocity) + 1, 0.25)
        velocity_labels = [f"{get_mt_km_speed_float(v):.2f}" for v in velocity_ticks]

        fig.update_layout(
            yaxis=dict(
                tickmode="array",
                tickvals=velocity_ticks,  # Raw velocity values as tick positions
                ticktext=velocity_labels,  # Converted min/km values as tick labels
                title={
                    "text": "Speed (min/km)",
                    "font": {"size": 18, "color": "#333333"},
                },
            )
        )

        return mo.vstack(
            [
                dropdown_activities,
                mo.ui.plotly(fig),
            ]
        )

    return (activity_focus,)


@app.cell
def _(alt, get_mt_km_speed, mo, pl):
    # We need a specific function to handle speed conversion
    # Moreover, since min/km distance is not interpretable as numbers
    # we plot a standard bar chart and manually produce bins
    def bar_chart_speed(_df):
        if _df.height == 1:
            return mo.callout(
                "Select more than one activity to view speed distribution!"
            )

        _df = (
            _df["average_speed"]
            .hist()
            .with_columns(
                extremes=pl.col("category")
                .cast(pl.String)
                .str.extract_all(r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")
            )
        )

        # here we invert max and min since higher km/h means lower min/km
        _df = (
            _df.with_columns(
                max=pl.col("extremes")
                .list.get(0)
                .cast(pl.Float32)
                .map_elements(get_mt_km_speed, return_dtype=pl.String),
                min=pl.col("extremes")
                .list.get(1)
                .cast(pl.Float32)
                .map_elements(get_mt_km_speed, return_dtype=pl.String),
            )
            .sort("min")
            .with_columns(
                range=pl.concat_str(pl.col("min"), pl.col("max"), separator=" - ")
            )
        )

        return (
            alt.Chart(
                _df,
                title=alt.TitleParams(
                    "Speed Distribution", anchor="middle", fontSize=18
                ),
            )
            .mark_bar()
            .encode(
                x=alt.X(
                    "range:O",
                    title="Speed (min/km)",
                    axis=alt.Axis(labelAngle=0, labelFontSize=12, titleFontSize=15),
                ),
                y=alt.Y(
                    "count",
                    title="Counts",
                    axis=alt.Axis(titleFontSize=15, labelAngle=0, labelFontSize=12),
                ),
            )
        )

    def bar_chart_distance(_df):
        if _df.height == 1:
            return mo.callout(
                "Select more than one activity to view speed distribution!"
            )

        _df = (
            _df["kms"]
            .hist()
            .with_columns(
                extremes=pl.col("category")
                .cast(pl.String)
                .str.extract_all(r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)")
            )
        )

        # Duplicate some code but fine, we are doing different things after all
        _df = (
            _df.with_columns(
                min=pl.col("extremes").list.get(0).cast(pl.Float32).round(2),
                max=pl.col("extremes").list.get(1).cast(pl.Float32).round(2),
            )
            .sort("min")
            .with_columns(
                range=pl.concat_str(pl.col("min"), pl.col("max"), separator=" - ")
            )
        )

        return (
            alt.Chart(
                _df,
                title=alt.TitleParams(
                    "Distance Distribution", anchor="middle", fontSize=18
                ),
            )
            .mark_bar()
            .encode(
                x=alt.X(
                    "range:O",
                    title="Distance (km)",
                    sort=None,  # prevent sorting otherwise "9" > "1"
                    axis=alt.Axis(labelAngle=0, labelFontSize=12, titleFontSize=15),
                ),
                y=alt.Y(
                    "count",
                    title="Counts",
                    axis=alt.Axis(titleFontSize=15, labelAngle=0, labelFontSize=12),
                ),
            )
        )

    return bar_chart_distance, bar_chart_speed


@app.cell
def _(alt, days, mo, pl):
    # unused because I ended up liking more the result of polars.hist
    def _bar_chart(_df, _column_name, _display_name, _unit_measure):
        if _df.height == 1:
            return mo.callout(
                f"Select more than one activity to view {_display_name} distribution!"
            )

        return (
            alt.Chart(
                _df,
                title=alt.TitleParams(
                    f"{_display_name.capitalize()} Distribution",
                    anchor="middle",
                    fontSize=18,
                ),
            )
            .mark_bar()
            .encode(
                x=alt.X(
                    f"{_column_name}:Q",
                    bin=True,
                    title=f"{_display_name.capitalize()} ({_unit_measure})",
                    axis=alt.Axis(labelAngle=0, labelFontSize=12, titleFontSize=15),
                ),
                y=alt.Y(
                    "count()",
                    title="Counts",
                    axis=alt.Axis(titleFontSize=15, labelAngle=0, labelFontSize=12),
                ),
            )
        )

    def heatmap_chart(_df):
        # 1. Add day, week and year columns
        # 2. Group by year, week and day, then agg on the sum
        # of kms to get the kilometers done on a certain day
        # 3. Sort by year, week and day to order entries
        # 4. Replace each day with its name
        # 5. Round kilometers to 2 decimal digits

        source = (
            _df.with_columns(
                day=pl.col("start_date").dt.weekday(),
                week=pl.col("start_date").dt.week(),
                year=pl.col("start_date").dt.iso_year(),
            )
            .group_by([pl.col("year"), pl.col("week"), pl.col("day")])
            .agg(
                pl.col("kms").sum(), pl.col("start_date").min(), pl.col("id")
            )  # keep also start date to show it in plot
            .with_columns(
                day=pl.col("day").replace_strict(days),
                year_week=pl.concat_str(
                    pl.col("year"), pl.col("week"), separator=" - "
                ),
                Date=pl.col("start_date"),
                Kilometers=pl.col("kms").round(2),
            )
        )

        sorted_years_week = sorted(
            source["year_week"].to_list(),
            key=lambda yw: tuple(map(lambda p: -int(p), yw.split(" - "))),
        )

        altair_chart = (
            alt.Chart(source)
            .mark_rect()
            .encode(
                x=alt.X(
                    "day:O",
                    title="Day of Week",
                    sort=list(days.values()),
                    axis=alt.Axis(
                        labelAngle=0, labelFontSize=12, titleFontSize=15, titleY=28
                    ),
                ),
                y=alt.Y(
                    "year_week:O",
                    title="Week",
                    sort=sorted_years_week,
                    axis=alt.Axis(labels=False, tickSize=0, titleFontSize=15),
                ),
                color=alt.Color(
                    "kms:Q",
                    title="Kilometers",
                    legend=alt.Legend(labelFontSize=12, titleFontSize=14),
                ).scale(),
                tooltip=["Date", "Kilometers"],
            )
        )

        return mo.ui.altair_chart(chart=altair_chart, chart_selection=True)

    return (heatmap_chart,)


@app.cell
def _(displayed_activities, mo):
    _options = displayed_activities["start_date_str"].to_list()
    dropdown_activities = mo.ui.multiselect(
        options=_options,
        label="Select activity",
        value=_options[:1],
        max_selections=10,
    )
    return (dropdown_activities,)


@app.cell
def _(math):
    def _get_n_digits(_n):
        if _n == 0:
            return 1

        # https://stackoverflow.com/questions/2189800/how-to-find-length-of-digits-in-an-integer
        return int(math.log10(_n)) + 1

    def get_nice_duration(_seconds):
        secs = int(_seconds)

        hours = secs // 3600
        minutes = secs % 3600 // 60
        seconds = secs % 3600 % 60

        hours = hours if _get_n_digits(hours) >= 2 else f"0{hours}"
        minutes = minutes if _get_n_digits(minutes) >= 2 else f"0{minutes}"
        seconds = seconds if _get_n_digits(seconds) >= 2 else f"0{seconds}"

        return f"{hours}:{minutes}:{seconds}"

    def get_column_sum(_df, _column_name):
        if _df.height == 0:
            return 0.0
        return _df[_column_name].sum()

    def get_average_column(_df, _column_name):
        if _df.height == 0:
            return 0.0
        return _df[_column_name].mean()

    def _from_mt_s_to_min_km(v) -> tuple[int, int]:
        if v == 0:
            return 0, 0

        min_per_km_dec = 1 / (v * 0.06)

        min_per_km_min = int(min_per_km_dec)
        min_per_km_secs = min_per_km_dec % 1 * 60

        return min_per_km_min, min_per_km_secs

    def get_mt_km_speed(v) -> str:
        mins, secs = _from_mt_s_to_min_km(v)

        mins = int(mins) if _get_n_digits(mins) >= 2 else f"0{int(mins)}"
        secs = int(secs) if _get_n_digits(secs) >= 2 else f"0{int(secs)}"

        return f"{mins}:{secs}"

    def get_mt_km_speed_float(v) -> str:
        mins, secs = _from_mt_s_to_min_km(v)

        mins = int(mins) if _get_n_digits(mins) >= 2 else f"0{int(mins)}"
        secs = int(secs) if _get_n_digits(secs) >= 2 else f"0{int(secs)}"

        return float(f"{mins}.{secs}")

    def get_average_speed(_df):
        if _df.height == 0:
            return 0.0

        mean_mt_s = _df["average_speed"].mean()

        # Stava returns speed as mt / s
        # Let's convert it to min / km

        mins, secs = _from_mt_s_to_min_km(mean_mt_s)

        secs = int(secs) if _get_n_digits(secs) >= 2 else f"0{int(secs)}"

        return f"{mins}:{secs}"

    return (
        get_average_column,
        get_average_speed,
        get_column_sum,
        get_mt_km_speed,
        get_mt_km_speed_float,
        get_nice_duration,
    )


@app.cell
def _(get_end_date, get_start_date, pl, whole_df):
    # Add 23:59:59 to end date
    # in order to make it "inclusive"

    # We filter to keep only running activities.
    # This can easily be extended to other activity types
    filtered_df = whole_df.filter(pl.col("sport_type") == "Run").filter(
        pl.col("start_date").is_between(
            get_start_date(), get_end_date().replace(hour=23, minute=59, second=59)
        )
    )
    return (filtered_df,)


@app.cell
def _(activities, pl):
    whole_df = pl.DataFrame(activities)

    # Add a km column since we'll need that often
    whole_df = whole_df.with_columns(kms=pl.col("distance") / 1000)
    return (whole_df,)


@app.cell
def _(client, mo, requests, time):
    # === ACTIVITY STREAM FUNCTION ===
    @mo.cache
    def fetch_activity_stream(activity_id: str, keys: list[str] | None = None):
        n_retries = 0

        while True:
            try:
                streams = client.get_activity_stream(
                    id=activity_id,
                    keys=keys,
                )
                break  # Success - exit retry loop

            except Exception as e:
                n_retries += 1
                if n_retries > 3:
                    return []

        return streams

    @mo.cache
    def fetch_mocked_activity_stream():
        url = "https://raw.githubusercontent.com/GiovanniGiacometti/strava-marimo-analyzer/main/mocked_data/mocked_streams.json"

        n_retries = 0

        # Retry loop for current page
        while n_retries <= 3:
            try:
                return requests.get(url).json()

            except Exception as e:
                n_retries += 1

                if n_retries > 3:
                    raise
                else:
                    wait_time = 2**n_retries
                    time.sleep(wait_time)

    return fetch_activity_stream, fetch_mocked_activity_stream


@app.cell
def _(
    client,
    client_ready,
    load_mocked_activities,
    mo,
    requests,
    strava_client,
    time,
):
    # === Activities ===

    @mo.cache
    def _fetch_activities():
        n_retries = 0

        with mo.status.spinner(title="Fetching activities...") as _spinner:
            _spinner.update("Fetching activities...")

            page = 1
            activities = []

            while True:
                if page > 30:  # Limit pages to avoid too many requests
                    break

                # Reset retry counter for each page
                n_retries = 0
                page_activities = None

                # Retry loop for current page
                while n_retries <= 3:
                    try:
                        page_activities = client.get_activities(page=page, per_page=200)
                        break  # Success - exit retry loop

                    except Exception as e:
                        n_retries += 1

                        if n_retries > 3:
                            break
                        else:
                            wait_time = 2**n_retries
                            time.sleep(wait_time)

                # Check if we successfully got data for this page
                if page_activities is None:
                    page += 1
                    continue

                # Check if page is empty (no more activities)
                if not page_activities:
                    break

                # Successfully got activities
                activities.extend(page_activities)

                # Move to next page
                page += 1

                # Small delay between successful requests
                time.sleep(0.5)

            return activities

    @mo.cache
    def _load_mocked_activities():
        url = "https://raw.githubusercontent.com/GiovanniGiacometti/strava-marimo-analyzer/main/mocked_data/mocked_activity.json"

        n_retries = 0

        # Retry loop for current page
        while n_retries <= 3:
            try:
                activities = requests.get(url).json()

                activities = [
                    strava_client.models.api.StravaActivity.model_validate_json(act)
                    for act in activities
                ]

                return activities  # Success - exit retry loop

            except Exception as e:
                n_retries += 1

                if n_retries > 3:
                    break
                else:
                    wait_time = 2**n_retries
                    time.sleep(wait_time)

    # If mocked data should be loaded, we proceed. Otherwise, we
    # wait for the client to be ready
    mo.stop(not client_ready and not load_mocked_activities)

    if load_mocked_activities:
        activities = _load_mocked_activities()
    else:
        # This should be optimized to load only necessary activities
        activities = _fetch_activities()
    return (activities,)


@app.cell
def _(datetime, mo, pd):
    # == CONSTANTS ==

    min_date = "2025-01-01"
    max_date = datetime.datetime.today().strftime("%Y-%m-%d")
    get_start_date, set_start_date = mo.state(pd.to_datetime(min_date))
    get_end_date, set_end_date = mo.state(pd.to_datetime(max_date))

    start_date = mo.ui.date(
        label="Start Date",
        value=get_start_date().strftime("%Y-%m-%d"),
        on_change=lambda x: set_start_date(pd.to_datetime(x)),
    )
    end_date = mo.ui.date(
        label="End Date",
        value=get_end_date().strftime("%Y-%m-%d"),
        on_change=lambda x: set_end_date(pd.to_datetime(x)),
    )

    # Mocked data switch
    use_mocked_data = mo.ui.switch(label="Use mocked data")

    days = {
        i + 1: d
        for i, d in enumerate(
            [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
        )
    }
    return (
        days,
        end_date,
        get_end_date,
        get_start_date,
        start_date,
        use_mocked_data,
    )


@app.cell
async def _():
    # =========================================================
    # Necessary when running as a WASM notebook

    import micropip

    await micropip.install("plotly")
    await micropip.install("python-dotenv")

    # Workaround to make it work with micropip
    micropip.uninstall("typing-extensions", verbose=True)
    await micropip.install("strava-client==1.0.5", verbose=True)
    await micropip.install("polars")

    # =========================================================

    import strava_client
    from strava_client import client as s_client
    import plotly
    import plotly.express as px
    import polars as pl
    import time

    from dotenv import load_dotenv

    import altair as alt
    import datetime
    import pandas as pd
    import math
    import numpy as np
    import sys
    import requests

    _ = load_dotenv()
    return (
        alt,
        datetime,
        math,
        np,
        pd,
        pl,
        plotly,
        px,
        requests,
        s_client,
        strava_client,
        sys,
        time,
    )


@app.cell
def _():
    # Importing marimo alone should make loading the MD blocks faster
    import marimo as mo

    return (mo,)


if __name__ == "__main__":
    app.run()
