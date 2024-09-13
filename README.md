## This bot is used on the official Dreamy Sky Sanctuary discord server, the bot offers the following features
- An fully working ticket system with an logging system
- An team creation system
- An music player with playlist and queue capabilities

Join the discord server and see the bot in action!: [DreamySkySanctuary](http://discord.gg/DreamySkySanctuary)

!!!the bot does require you to have FFMpeg added to you PATH variable

the `.env` file needs to have the bot token put in it
```python
    DISCORD_TOKEN=<Bot_token>

    INVITE_URL="""
        https://discord.com/oauth2/authorize?client_id=
    """ # bot invite url for ease of access
```

The settings of the bot are pretty simple. They are located in `.\Bot\main.py`.
Just change the following variables to suite your discord server

``` python 
    # these are the ID's of the different roles on the server, all except for the sancturary_keeper and event_luminary are required to be set in order for the bot to work
    sancturary_keeper_role_id: int = <role_ID> # owner Rol ID
    sky_guardians_role_id: int = <role_ID> # responds to and mannages tickets 
    tech_oracle_role_id: int = <role_ID> # can create an private Dev channel if needed
    event_luminary_role_id: int = <role_ID> # here so they can create teams
    
    allowed_roles: list[int] = [<sancturary_keeper_role_id>, <sky_guardians_role_id>, ...] # these are the rols that are allowed to create teams and sutch
    
    support_category_id: int = <category_ID> # this ID needs to be set for the ticket system to be able to create a ticket
    general_category_id: int = <category_ID> # this ID needs to be set for the bot to create private Def channels 
    music_voice_id: int = <voice_channel_ID> # this ID needs to be set so that the bot can only join that specific voice channel

    bot_channel: str = <channel_name> # does nothing ATM
    music_channel: str = <channel_name> # this is the channel where all the music info will be send
    ticket_channel: str = <channel_name> # this is the channel that will let people create tickets
    ticket_logs_channel: str = <channel_name> # this is the hidden channel where all the ticket logs will be send

    max_teams: int = 4 # this can be changed to allow for more or less than 4 teams

    # the rest of the options do not need to be edited
```

## Authors

- **Leafy** - *Initial work* - [Ralsey](https://github.com/Ralsey)
- **Sander1946** - *main contibuter* - [Sander1946](https://github.com/sander1946)



## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details