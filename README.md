My discord bot written with AI.
Dreamybot

Which holds a ticket system and a team system.

The discord server is: Http://discord.gg/DreamySkySanctuary

the `.env` file needs to have the bot token put in it
```python
    DISCORD_TOKEN=<Bot_token>

    INVITE_URL="""
        https://discord.com/oauth2/authorize?client_id=
    """ # bot invite url for ease of access
```

settings are pretty simple, just change te following ID's to match with your server

``` python 
    allowed_roles: list[int] = [<role_ID_1>, <role_ID_1>, ...] # these are the rols that are allowed to create teams and sutch
    sky_guardians_role_id: int = <role_ID> # this is the rol ID of the people that will help with the tickes that are created
    owner_id: int = <user_ID> # the user ID of the owner/head moderator where a personal message will be send when a ticket is created
    support_category_id = <category_ID> # the chanel category ID under wich the ticket chanels will be created
```

the bot requires you to have 2 specific chanels, `🎫query-corner` and `🎟ticket-logs`, these names can be changed in the code