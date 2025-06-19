# Strava Marimo Analyzer 🏃‍♀️‍➡️​🏃‍➡️!

A [Marimo](https://docs.marimo.io/) notebook for visualizing and analyzing your [Strava](https://strava.com/) activity data!

🚀 Powered by:
- [`strava-client`](https://github.com/GiovanniGiacometti/strava-client)
- [`polars`](https://pola.rs/)
- [`altair`](https://altair-viz.github.io/index.html)
- [`plotly`](https://plotly.com/).

🌐 A web-based version, running entirely in your browser via WebAssembly (WASM), is available [here](https://giovannigiacometti.it/strava-marimo-analyzer/).

## ✨ Features


## 📥 Get Started with your data!

To begin, you'll need to authenticate your Strava account. The full process is explained in the [strava-client documentation](https://github.com/GiovanniGiacometti/strava-client?tab=readme-ov-file#authentication).


### If you are running this notebook locally

You can either provide your credentials through a .env file or set them directly in your terminal. When you run the notebook for the first time, a browser tab will open to authenticate your Strava account and retrieve an access token. All information are saved in a file called `.strava.secrets` file so you won’t need to re-authenticate in future sessions.

### If you are using the web-based WASM version

you’ll need to manually enter your credentials into the form at the top of the notebook. Since the browser cannot perform the full authentication flow, you must retrieve the necessary information beforehand — for instance by using the `strava-client` locally. Note that this information is not stored in the browser, so you'll need to re-enter it each time you reload the page.
