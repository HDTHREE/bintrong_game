from dash import dcc


token_store = dcc.Store("token", "session")


user_store = dcc.Store("user", "session")


interval = dcc.Interval("interval", 3.6e5)


url = dcc.Location(id="url")

game_player_store = dcc.Store("game-player", "session")
