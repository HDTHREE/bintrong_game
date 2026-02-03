from dash import dcc


token_store = dcc.Store("token", "session")


user_store = dcc.Store("user", "session")


interval = dcc.Interval("interval", 1.8e5)


url = dcc.Location(id="url")
