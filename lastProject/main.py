import os
from functools import partial

from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.navigationdrawer import MDNavigationLayout

from repository import GameRepository


class RootWidget(MDNavigationLayout):
    pass


class GameCard(MDCard):
    def __init__(self, game_id, source_screen, **kwargs):
        super().__init__(**kwargs)
        self.register_event_type("on_release")
        self.game_id = game_id
        self.source_screen = source_screen

    def on_release(self):
        pass

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos) and not touch.is_mouse_scrolling:
            self.dispatch("on_release")
            return True
        return super().on_touch_up(touch)


class UniversalGameLibraryApp(MDApp):
    bg_color = ListProperty([0, 0, 0, 1])
    surface_color = ListProperty([0.06, 0.06, 0.08, 1])
    card_color = ListProperty([0.09, 0.09, 0.14, 1])
    panel_color = ListProperty([0.08, 0.08, 0.1, 1])
    chip_color = ListProperty([0.12, 0.1, 0.16, 1])
    drawer_color = ListProperty([0.05, 0.05, 0.07, 1])
    text_color = ListProperty([0.95, 0.95, 1, 1])
    subtext_color = ListProperty([0.7, 0.7, 0.85, 1])
    muted_text_color = ListProperty([0.6, 0.6, 0.7, 1])
    current_theme = StringProperty("dark")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        base_dir = os.path.dirname(__file__)
        self.base_dir = base_dir
        self.project_dir = os.path.dirname(base_dir)
        self.repo = GameRepository(base_dir)
        self.selected_game_id = None
        self.previous_screen = "home"
        self.catalog_sort = "popularity"
        self.catalog_sort_dir = "desc"
        self.search_open = False
        self.filter_open = False
        self.library_status = "all"
        self.profile_name = "Player One"
        self.catalog_page = 1
        self.library_page = 1
        self.page_size = 6
        self.sort_menu = None
        self._theme_updating = False

    def build(self):
        self.title = "Universal Game Library Tracker"
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.accent_palette = "Purple"
        Window.clearcolor = (0, 0, 0, 1)
        kv_path = os.path.join(os.path.dirname(__file__), "layout.kv")
        Builder.load_file(kv_path)
        return RootWidget()

    def on_start(self):
        self.repo.initialize()
        self.update_platform_filters()
        self.set_screen("home")
        self.update_profile_label()
        self.set_theme("dark")

    def set_screen(self, screen_name):
        self._screen_manager().current = screen_name
        if screen_name == "home":
            self.load_catalog()
        elif screen_name == "my_games":
            self.load_library()
        elif screen_name == "account":
            self.load_account_stats()
        elif screen_name == "detail" and self.selected_game_id:
            self.load_detail(self.selected_game_id)

    def nav_to(self, screen_name):
        self.root.ids.nav_drawer.set_state("close")
        self.set_screen(screen_name)

    def toggle_drawer(self):
        drawer = self.root.ids.nav_drawer
        drawer.set_state("open" if drawer.state == "close" else "close")

    def go_back(self):
        self.set_screen(self.previous_screen)

    def open_detail(self, game_id, source_screen, *args):
        self.selected_game_id = game_id
        self.previous_screen = source_screen
        self.set_screen("detail")

    def open_sort_menu(self):
        screen = self._screen("home")
        caller = screen.ids.catalog_sort_button
        if self.sort_menu:
            self.sort_menu.caller = caller
            self.sort_menu.open()
            return
        items = [
            {
                "text": "Popular",
                "viewclass": "OneLineListItem",
                "on_release": lambda s="popularity", d="desc", t="Popular": self.set_sort(
                    s, d, t
                ),
            },
            {
                "text": "Name A-Z",
                "viewclass": "OneLineListItem",
                "on_release": lambda s="title", d="asc", t="Name A-Z": self.set_sort(
                    s, d, t
                ),
            },
            {
                "text": "Name Z-A",
                "viewclass": "OneLineListItem",
                "on_release": lambda s="title", d="desc", t="Name Z-A": self.set_sort(
                    s, d, t
                ),
            },
            {
                "text": "Newest",
                "viewclass": "OneLineListItem",
                "on_release": lambda s="release_year", d="desc", t="Newest": self.set_sort(
                    s, d, t
                ),
            },
            {
                "text": "Oldest",
                "viewclass": "OneLineListItem",
                "on_release": lambda s="release_year", d="asc", t="Oldest": self.set_sort(
                    s, d, t
                ),
            },
        ]
        self.sort_menu = MDDropdownMenu(
            caller=caller,
            items=items,
            width_mult=3,
        )
        self.sort_menu.open()

    def set_sort(self, sort_by, sort_dir, label):
        self.catalog_sort = sort_by
        self.catalog_sort_dir = sort_dir
        screen = self._screen("home")
        screen.ids.catalog_sort_label.text = label
        self.catalog_page = 1
        if self.sort_menu:
            self.sort_menu.dismiss()
        self.load_catalog()

    def toggle_search(self):
        screen = self._screen("home")
        container = screen.ids.catalog_search_container
        self.search_open = not self.search_open
        container.height = dp(48) if self.search_open else 0
        container.opacity = 1 if self.search_open else 0
        container.disabled = not self.search_open
        if not self.search_open:
            screen.ids.catalog_search.text = ""
            self.load_catalog()

    def toggle_filter_panel(self):
        screen = self._screen("home")
        card = screen.ids.catalog_filter_card
        self.filter_open = not self.filter_open
        card.height = card.minimum_height if self.filter_open else 0
        card.opacity = 1 if self.filter_open else 0
        card.disabled = not self.filter_open

    def on_search_text(self, value):
        if self.search_open:
            self.catalog_page = 1
            self.load_catalog()

    def clear_catalog_filters(self):
        screen = self._screen("home")
        screen.ids.catalog_year_from.text = ""
        screen.ids.catalog_year_to.text = ""
        screen.ids.catalog_publisher.text = ""
        screen.ids.catalog_developer.text = ""
        screen.ids.catalog_platform.text = "All Platforms"
        screen.ids.catalog_genre.text = ""
        self.catalog_page = 1
        self.load_catalog()

    def apply_catalog_filters(self):
        self.catalog_page = 1
        self.load_catalog()

    def load_catalog(self):
        filters = self.collect_catalog_filters()
        games = self.repo.list_master_games(filters)
        games = self.sort_games(games, self.catalog_sort, self.catalog_sort_dir)
        screen = self._screen("home")
        self.update_paging(screen, games, "catalog")

    def load_library(self):
        filters = self.collect_library_filters()
        games = self.repo.list_library_games(filters)
        games = self.sort_games(games, "title", "asc")
        screen = self._screen("my_games")
        self.update_library_filter_buttons()
        self.update_paging(screen, games, "library")

    def load_account_stats(self):
        stats = self.repo.stats_summary()
        screen = self._screen("account")
        screen.ids.stats_total.text = str(stats["total_games"])
        screen.ids.stats_owned.text = str(stats["owned"])
        screen.ids.stats_played.text = str(stats["played"])
        screen.ids.stats_completed.text = str(stats["completed"])
        screen.ids.stats_full.text = str(stats["full"])
        screen.ids.stats_ratio.text = f"{stats['completion_ratio']:.1f}%"

    def build_game_card(self, game, screen_name):
        card_height = dp(210) if screen_name == "my_games" else dp(190)
        card = GameCard(
            game_id=game["id"],
            source_screen=screen_name,
            size_hint_y=None,
            height=card_height,
            radius=[16, 16, 16, 16],
            md_bg_color=self.card_color,
            elevation=2,
        )
        card.bind(on_release=partial(self.open_detail, game["id"], screen_name))

        layout = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6))
        cover_source = self._first_screenshot(game)
        cover = MDCard(
            size_hint_y=None,
            height=dp(96),
            radius=[12, 12, 12, 12],
            md_bg_color=self.chip_color,
            elevation=0,
        )
        if cover_source:
            cover.add_widget(Image(source=cover_source, fit_mode="cover"))
        else:
            cover.add_widget(
                MDLabel(
                    text="Cover",
                    halign="center",
                    valign="middle",
                    theme_text_color="Custom",
                    text_color=self.subtext_color,
                )
            )
        title = MDLabel(
            text=game["title"],
            font_style="Subtitle1",
            theme_text_color="Custom",
            text_color=self.text_color,
            size_hint_y=None,
            height=dp(36),
        )
        year = MDLabel(
            text=str(game["release_year"]),
            theme_text_color="Custom",
            text_color=self.subtext_color,
            size_hint_y=None,
            height=dp(20),
        )
        layout.add_widget(cover)
        layout.add_widget(title)
        layout.add_widget(year)
        if screen_name == "my_games":
            progress_pct = int(game.get("completion_pct") or 0)
            progress = MDLabel(
                text=f"Progress: {progress_pct}%",
                theme_text_color="Custom",
                text_color=self.subtext_color,
                size_hint_y=None,
                height=dp(18),
            )
            layout.add_widget(progress)
        card.add_widget(layout)
        return card

    def collect_catalog_filters(self):
        screen = self._screen("home")
        platform = screen.ids.catalog_platform.text.strip()
        if platform == "All Platforms":
            platform = ""
        return {
            "search": screen.ids.catalog_search.text.strip(),
            "platform": platform,
            "genre": screen.ids.catalog_genre.text.strip(),
            "publisher": screen.ids.catalog_publisher.text.strip(),
            "developer": screen.ids.catalog_developer.text.strip(),
            "year_from": self._parse_int(screen.ids.catalog_year_from.text),
            "year_to": self._parse_int(screen.ids.catalog_year_to.text),
            "sort_by": self.catalog_sort,
            "sort_dir": self.catalog_sort_dir,
        }

    def collect_library_filters(self):
        filters = {
            "sort_by": "title",
            "sort_dir": "asc",
        }
        if self.library_status == "owned":
            filters["owned_only"] = True
        elif self.library_status == "played":
            filters["played_only"] = True
        elif self.library_status == "main_story":
            filters["main_story_only"] = True
        elif self.library_status == "full":
            filters["full_only"] = True
        return filters

    def set_library_status(self, status):
        self.library_status = status
        self.library_page = 1
        self.load_library()

    def update_library_filter_buttons(self):
        screen = self._screen("my_games")
        mapping = {
            "all": screen.ids.library_filter_all,
            "owned": screen.ids.library_filter_owned,
            "played": screen.ids.library_filter_played,
            "main_story": screen.ids.library_filter_main_story,
            "full": screen.ids.library_filter_full,
        }
        for key, button in mapping.items():
            is_active = key == self.library_status
            button.md_bg_color = (0.32, 0.18, 0.5, 1) if is_active else (0, 0, 0, 0)
            button.text_color = (1, 1, 1, 1) if is_active else (0.8, 0.8, 0.9, 1)

    def load_detail(self, game_id):
        game = self.repo.get_game(game_id)
        if not game:
            return
        screen = self._screen("detail")
        screen.ids.detail_title.text = game["title"]
        description = game.get("description") or ""
        screen.ids.detail_description.text = (
            f"Year: {game['release_year']}\n\n"
            f"Genre: {game['genres']}\n\n"
            f"Platform: {game['platforms']}\n\n"
            f"Publisher: {game['publisher']}\n\n"
            f"Developer: {game['developer']}\n\n"
            f"Short desc: {description}"
        )
        screen.ids.detail_platforms_played.text = (
            game.get("platforms_played") or "Select platform"
        )
        screen.ids.detail_owned.active = bool(game["owned"])
        screen.ids.detail_played.active = bool(game["played"])
        screen.ids.detail_main_story.active = bool(game.get("main_story_completed"))
        screen.ids.detail_completion.value = float(game["completion_pct"])
        screen.ids.detail_completion_label.text = f"{int(game['completion_pct'])}%"
        screen.ids.detail_completion_year.text = game.get("completion_year") or ""
        screen.ids.detail_hours.text = str(game["hours_played"])
        screen.ids.detail_notes.text = game["notes"]
        updated = game["last_updated"] or "Never"
        screen.ids.detail_updated.text = f"Last updated: {updated}"
        self.update_status_line(screen, game)
        self.populate_gallery(screen, game)

    def populate_gallery(self, screen, game):
        gallery = screen.ids.detail_gallery
        gallery.clear_widgets()
        shots = [
            shot.strip()
            for shot in (game.get("screenshots") or "").split("|")
            if shot.strip()
        ]
        if not shots:
            shots = ["Screenshot"]
        for index, shot in enumerate(shots, start=1):
            card = MDCard(
                size_hint=(1, 1),
                size_hint_y=None,
                height=gallery.height,
                radius=[12, 12, 12, 12],
                md_bg_color=self.chip_color,
                elevation=0,
            )
            source = self._resolve_media_path(shot)
            if source:
                card.add_widget(Image(source=source, fit_mode="cover"))
            else:
                card.add_widget(
                    MDLabel(
                        text=f"Shot {index}",
                        halign="center",
                        valign="middle",
                        theme_text_color="Custom",
                        text_color=self.subtext_color,
                    )
                )
            gallery.add_widget(card)
        if hasattr(gallery, "index"):
            gallery.index = 0

    def gallery_prev(self):
        screen = self._screen("detail")
        screen.ids.detail_gallery.load_previous()

    def gallery_next(self):
        screen = self._screen("detail")
        screen.ids.detail_gallery.load_next()

    def update_completion_label(self, value):
        screen = self._screen("detail")
        screen.ids.detail_completion_label.text = f"{int(value)}%"
        self.refresh_detail_status()

    def refresh_detail_status(self):
        screen = self._screen("detail")
        game = {
            "owned": screen.ids.detail_owned.active,
            "played": screen.ids.detail_played.active,
            "main_story_completed": screen.ids.detail_main_story.active,
            "completion_pct": int(screen.ids.detail_completion.value),
        }
        self.update_status_line(screen, game)

    def update_status_line(self, screen, game):
        flags = []
        if game.get("owned"):
            flags.append("Owned")
        if game.get("played"):
            flags.append("Played")
        if game.get("main_story_completed"):
            flags.append("Main story completed")
        completion_pct = int(game.get("completion_pct") or 0)
        if completion_pct > 0 and completion_pct < 100:
            flags.append(f"Progress {completion_pct}%")
        if completion_pct == 100:
            flags.append("Completed 100%")
        status_text = ", ".join(flags) if flags else "No status set"
        screen.ids.detail_status_line.text = f"Status: {status_text}"

    def save_detail(self):
        if not self.selected_game_id:
            return
        screen = self._screen("detail")
        owned = screen.ids.detail_owned.active
        played = screen.ids.detail_played.active
        main_story_completed = screen.ids.detail_main_story.active
        completion_pct = int(screen.ids.detail_completion.value)
        if completion_pct > 0:
            played = True
            screen.ids.detail_played.active = True
        hours_played, hours_invalid = self._coerce_float(screen.ids.detail_hours.text)
        if hours_invalid:
            screen.ids.detail_hours.text = "0"
        completion_year = screen.ids.detail_completion_year.text.strip()
        notes = screen.ids.detail_notes.text.strip()
        platforms_played = screen.ids.detail_platforms_played.text.strip()
        if platforms_played == "Select platform":
            platforms_played = ""
        self.repo.upsert_user_game(
            self.selected_game_id,
            owned,
            played,
            main_story_completed,
            completion_pct,
            hours_played,
            notes,
            completion_year,
            platforms_played,
        )
        self.load_detail(self.selected_game_id)
        self.load_library()
        self.load_account_stats()

    def update_profile(self):
        screen = self._screen("account")
        nickname = screen.ids.account_nickname.text.strip()
        if nickname:
            self.profile_name = nickname
        self.update_profile_label()

    def update_profile_label(self):
        account = self._screen("account")
        account.ids.account_name.text = self.profile_name
        self.root.ids.drawer_name.text = self.profile_name

    def update_platform_filters(self):
        platforms = self.repo.list_platforms()
        home = self._screen("home")
        detail = self._screen("detail")
        home_spinner = home.ids.catalog_platform
        detail_spinner = detail.ids.detail_platforms_played
        home_spinner.values = ["All Platforms"] + platforms
        detail_spinner.values = ["Select platform"] + platforms
        if home_spinner.text not in home_spinner.values:
            home_spinner.text = "All Platforms"
        if detail_spinner.text not in detail_spinner.values:
            detail_spinner.text = "Select platform"

    def toggle_theme(self, is_dark):
        self.set_theme("dark" if is_dark else "light")

    def set_theme(self, mode):
        if self._theme_updating:
            return
        self._theme_updating = True
        is_dark = mode == "dark"
        self.current_theme = "dark" if is_dark else "light"
        self.theme_cls.theme_style = "Dark" if is_dark else "Light"
        if is_dark:
            self.bg_color = [0, 0, 0, 1]
            self.surface_color = [0.06, 0.06, 0.08, 1]
            self.card_color = [0.09, 0.09, 0.14, 1]
            self.panel_color = [0.08, 0.08, 0.1, 1]
            self.chip_color = [0.12, 0.1, 0.16, 1]
            self.drawer_color = [0.05, 0.05, 0.07, 1]
            self.text_color = [0.95, 0.95, 1, 1]
            self.subtext_color = [0.7, 0.7, 0.85, 1]
            self.muted_text_color = [0.6, 0.6, 0.7, 1]
        else:
            self.bg_color = [0.98, 0.98, 1, 1]
            self.surface_color = [0.92, 0.92, 0.95, 1]
            self.card_color = [0.96, 0.96, 0.98, 1]
            self.panel_color = [0.94, 0.94, 0.96, 1]
            self.chip_color = [0.9, 0.9, 0.94, 1]
            self.drawer_color = [0.93, 0.93, 0.96, 1]
            self.text_color = [0.18, 0.18, 0.22, 1]
            self.subtext_color = [0.35, 0.35, 0.45, 1]
            self.muted_text_color = [0.45, 0.45, 0.55, 1]
        Window.clearcolor = self.bg_color
        if self.root:
            prefs = self._screen("preferences")
            prefs.ids.pref_dark_mode.active = is_dark
            prefs.ids.pref_light_mode.active = not is_dark
        self._theme_updating = False

    def sort_games(self, games, sort_by, sort_dir):
        reverse = str(sort_dir).lower() == "desc"
        if sort_by == "release_year":
            return sorted(
                games,
                key=lambda item: int(item.get("release_year") or 0),
                reverse=reverse,
            )
        if sort_by == "popularity":
            return sorted(
                games,
                key=lambda item: int(item.get("popularity") or 0),
                reverse=reverse,
            )
        return sorted(games, key=lambda item: str(item.get("title") or "").lower(), reverse=reverse)

    def update_paging(self, screen, games, prefix):
        total = len(games)
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        if prefix == "catalog":
            self.catalog_page = min(self.catalog_page, total_pages)
            page = self.catalog_page
            label = screen.ids.catalog_page_label
            prev_btn = screen.ids.catalog_prev_button
            next_btn = screen.ids.catalog_next_button
        else:
            self.library_page = min(self.library_page, total_pages)
            page = self.library_page
            label = screen.ids.library_page_label
            prev_btn = screen.ids.library_prev_button
            next_btn = screen.ids.library_next_button
        label.text = f"Page {page} / {total_pages}"
        prev_btn.disabled = page <= 1
        next_btn.disabled = page >= total_pages
        start = (page - 1) * self.page_size
        end = start + self.page_size
        grid = screen.ids.catalog_grid if prefix == "catalog" else screen.ids.library_grid
        grid.clear_widgets()
        for game in games[start:end]:
            screen_name = "home" if prefix == "catalog" else "my_games"
            grid.add_widget(self.build_game_card(game, screen_name))

    def catalog_next_page(self):
        self.catalog_page += 1
        self.load_catalog()

    def catalog_prev_page(self):
        self.catalog_page = max(1, self.catalog_page - 1)
        self.load_catalog()

    def library_next_page(self):
        self.library_page += 1
        self.load_library()

    def library_prev_page(self):
        self.library_page = max(1, self.library_page - 1)
        self.load_library()

    def _parse_int(self, value):
        value = (value or "").strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    def _coerce_float(self, value):
        value = (value or "").strip()
        if not value:
            return 0.0, False
        try:
            return float(value), False
        except ValueError:
            return 0.0, True

    def _resolve_media_path(self, source):
        source = (source or "").strip()
        if not source:
            return ""
        if os.path.isabs(source) and os.path.exists(source):
            return source
        for base in (self.base_dir, self.project_dir):
            candidate = os.path.join(base, source)
            if os.path.exists(candidate):
                return candidate
        return ""

    def _first_screenshot(self, game):
        shots = (game.get("screenshots") or "").split("|")
        for shot in shots:
            path = self._resolve_media_path(shot)
            if path:
                return path
        return ""

    def _screen_manager(self):
        return self.root.ids.screen_manager

    def _screen(self, screen_name):
        return self._screen_manager().get_screen(screen_name)


if __name__ == "__main__":
    UniversalGameLibraryApp().run()
