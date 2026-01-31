from dash import dcc


token_store = dcc.Store("token", "local")


user_store = dcc.Store("user", "local")


interval = dcc.Interval("interval", 1.8e5)


url = dcc.Location(id="url")
