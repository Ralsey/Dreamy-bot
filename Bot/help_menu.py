from typing import List, Optional

import discord
from discord.ui import Select, View


class DeleteView(View):
    """
    The actual View for controlling the menu interaction

    Args:
        pages (List[discord.Embed], optional): List of pages the cycle through. Defaults to None.
        timeout (Optional[float], optional): The duration the interaction will be active for. Defaults to None.
        ephemeral (Optional[bool], optional): Send as an ephemeral message. Defaults to False.
    """

    index = 0

    def __init__(
        self,
        pages: List[discord.Embed] = None,
        timeout: Optional[float] = None,
        ephemeral: Optional[bool] = False,
        allowed_user: Optional[discord.Member] = None,
    ):
        super().__init__(timeout=timeout)
        self.page_count = len(pages) if pages else None
        self.pages = pages
        self.allowed_user = allowed_user

        if pages and len(pages) == 1:
            self.remove_item(self.previous)
            self.remove_item(self.next)
            self.remove_item(self.select)

        if ephemeral:
            self.remove_item(self._delete)

        if pages and len(pages) > 1:
            for index, page in enumerate(pages):
                self.select.add_option(
                    label=f"{page.title}",
                    description=f"{page.description[:96]}...".replace("`", ""),
                    value=index,
                )

    @discord.ui.button(
        label="Previous",
        style=discord.ButtonStyle.success,
        row=1,
        custom_id="pretty_help:previous",
    )
    async def previous(self, interaction: discord.Interaction, button: discord.Button):
        self.index -= 1
        await self.update(interaction)

    @discord.ui.button(
        label="Next",
        style=discord.ButtonStyle.primary,
        row=1,
        custom_id="pretty_help:next",
    )
    async def next(self, interaction: discord.Interaction, button: discord.Button):
        self.index += 1
        await self.update(interaction)

    @discord.ui.button(
        label="Delete",
        style=discord.ButtonStyle.danger,
        row=1,
        custom_id="pretty_help:delete",
    )
    async def _delete(self, interaction: discord.Interaction, button: discord.Button):
        await interaction.message.delete()

    @discord.ui.select(row=2, custom_id="pretty_help:select")
    async def select(self, interaction: discord.Interaction, select: Select):
        self.index = int(select.values[0])
        await self.update(interaction)

    async def update(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            embed=self.pages[self.index % self.page_count], view=self
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            not self.allowed_user
            and interaction.data.get("custom_id") == self._delete.custom_id
        ):
            return True
        return interaction.user == self.allowed_user


class CreateButton(View):
    def __init__(self, *, timeout: float | None = 180):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(label="Create", style=discord.ButtonStyle.primary, custom_id="create")
    async def create(self, interaction: discord.Interaction):
        await interaction.response.send_message("Created!", ephemeral=True)
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, custom_id="cancel")
    async def cancel(self, interaction: discord.Interaction):
        await interaction.response.send_message("Cancelled!", ephemeral=True)
        self.stop()
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == 1234567890
    
    async def on_timeout(self) -> None:
        
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        self.stop()
        return await self.message.edit(view=self)
    
    async def on_error(self, error: Exception, item: discord.ui.Item, interaction: discord.Interaction) -> None:
        return await interaction.response.send_message("An error occurred!", ephemeral=True)
    