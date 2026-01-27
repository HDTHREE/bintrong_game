from dash import dcc


token_store = dcc.Store("token", "local")


user_store = dcc.Store("user", "local")
