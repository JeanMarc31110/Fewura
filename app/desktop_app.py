import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
import tkinter as tk
from tkinter import messagebox, ttk


API_BASE = "http://127.0.0.1:3000"
BG = "#f7f8fc"
CARD = "#ffffff"
INK = "#111a3a"
MUTED = "#65718b"
ACCENT = "#6547ed"
ACCENT_DARK = "#0c1238"
ACCENT_SOFT = "#f0edff"
SUCCESS = "#16a46a"
BLUE = "#2684ff"
AMBER = "#f2b84b"
LINE = "#e7e9f0"


class ApiError(Exception):
    pass


def api_request(path, method="GET", payload=None):
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{API_BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(detail).get("error", detail)
        except json.JSONDecodeError:
            pass
        raise ApiError(str(detail)) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise ApiError("Le serveur CRM est inaccessible. Relancez FÉWURA.") from error


class FewuraDesktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FÉWURA · Sales CRM")
        self.geometry("1460x900")
        self.minsize(1180, 720)
        self.configure(bg=BG)
        self.results = []
        self.prospects = []
        self.tasks = []
        self.dashboard = {}
        self.current_view = "overview"
        self.stage_labels = {
            "new": "Nouveau", "qualified": "Qualifié", "contacted": "Contacté",
            "replied": "Réponse reçue", "meeting": "Rendez-vous", "proposal": "Proposition",
            "won": "Gagné", "lost": "Perdu", "excluded": "Exclus",
        }
        self.priority_labels = {"high": "Haute", "normal": "Normale", "low": "Basse"}
        self.task_status_labels = {"open": "Ouverte", "in_progress": "En cours", "done": "Terminée", "cancelled": "Annulée"}
        self._build_style()
        self._build_shell()
        self.show_view("overview")

    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD, relief="solid", borderwidth=1)
        style.configure("TLabel", background=BG, foreground=INK, font=("Segoe UI", 10))
        style.configure("Card.TLabel", background=CARD, foreground=INK, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BG, foreground=INK, font=("Segoe UI", 25, "bold"))
        style.configure("CardTitle.TLabel", background=CARD, foreground=INK, font=("Segoe UI", 13, "bold"))
        style.configure("KpiValue.TLabel", background=CARD, foreground=INK, font=("Segoe UI", 22, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8), foreground=INK, background=CARD)
        style.configure("Primary.TButton", background=ACCENT, foreground="#ffffff", font=("Segoe UI", 10, "bold"), padding=(13, 9))
        style.map("Primary.TButton", background=[("active", "#5337d3"), ("pressed", "#4127b6")])
        style.configure("Treeview", rowheight=32, font=("Segoe UI", 9), background=CARD, fieldbackground=CARD, foreground=INK, borderwidth=0)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#f5f6fb", foreground=MUTED, relief="flat")
        style.map("Treeview", background=[("selected", "#eeeaff")], foreground=[("selected", INK)])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(18, 10), font=("Segoe UI", 10, "bold"))

    def _build_shell(self):
        self.sidebar = tk.Frame(self, bg=ACCENT_DARK, width=228)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, bg=ACCENT_DARK)
        brand.pack(fill="x", padx=22, pady=(25, 30))
        tk.Label(brand, text="F", bg=ACCENT, fg="#ffffff", font=("Segoe UI", 20, "bold"), width=2).pack(side="left", padx=(0, 11))
        tk.Label(brand, text="FÉWURA", bg=ACCENT_DARK, fg="white", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(brand, text="SALES CRM", bg=ACCENT_DARK, fg="#aeb9e8", font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.nav_buttons = {}
        for key, label in [("overview", "◉  Tableau de bord"), ("prospects", "♙  Prospects & comptes"), ("opportunities", "▥  Opportunités"), ("tasks", "✓  Tâches & activités"), ("prospecting", "➤  Prospection agent")]:
            self.nav_buttons[key] = self._nav_button(label, key)
        tk.Frame(self.sidebar, bg="#242d61", height=1).pack(fill="x", padx=22, pady=24)
        tk.Label(self.sidebar, text="PIPELINE COMMERCIAL", bg=ACCENT_DARK, fg="#8e9bd4", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=24)
        self.sidebar_pipeline_var = tk.StringVar(value="Chargement…")
        tk.Label(self.sidebar, textvariable=self.sidebar_pipeline_var, bg=ACCENT_DARK, fg="#d9def7", justify="left", font=("Segoe UI", 9), wraplength=185).pack(anchor="w", padx=24, pady=(8, 0))
        self.status_var = tk.StringVar(value="Prêt")
        profile = tk.Frame(self.sidebar, bg="#151d4b", highlightbackground="#2b3670", highlightthickness=1)
        profile.pack(side="bottom", fill="x", padx=14, pady=(0, 8))
        tk.Label(profile, text="JM", bg="#dfe4ff", fg=ACCENT, font=("Segoe UI", 10, "bold"), width=3, height=1).pack(side="left", padx=10, pady=10)
        tk.Label(profile, text="Jean Marc\nAdministrateur", bg="#151d4b", fg="#ffffff", justify="left", font=("Segoe UI", 9, "bold")).pack(side="left", pady=8)
        tk.Label(self.sidebar, textvariable=self.status_var, bg="#202a5d", fg="#d9def7", font=("Segoe UI", 8, "bold"), padx=12, pady=7).pack(side="bottom", fill="x", padx=14, pady=(0, 14))
        self.main = tk.Frame(self, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)

    def _nav_button(self, label, key):
        button = tk.Button(self.sidebar, text=label, command=lambda: self.show_view(key), bg=ACCENT_DARK, fg="#d9def7", activebackground="#4d3dc1", activeforeground="#ffffff", relief="flat", anchor="w", padx=18, pady=12, font=("Segoe UI", 10, "bold"), bd=0)
        button.pack(fill="x", padx=10, pady=2)
        return button

    def _clear_main(self):
        for child in self.main.winfo_children():
            child.destroy()

    def show_view(self, view):
        self.current_view = view
        self._clear_main()
        for key, button in self.nav_buttons.items():
            button.configure(bg="#4d3dc1" if key == view else ACCENT_DARK, fg="#ffffff" if key == view else "#d9def7")
        if view == "overview":
            self._build_overview()
            self.load_dashboard()
        elif view == "prospects":
            self._build_prospects()
            self.load_prospects()
        elif view == "opportunities":
            self._build_opportunities()
            self.load_prospects()
        elif view == "tasks":
            self._build_tasks()
            self.load_tasks()
        else:
            self._build_prospecting()

    def _page_header(self, eyebrow, title, subtitle, action=None):
        header = tk.Frame(self.main, bg=BG)
        header.pack(fill="x", padx=40, pady=(28, 20))
        copy = tk.Frame(header, bg=BG)
        copy.pack(side="left")
        tk.Label(copy, text=eyebrow.upper(), bg=BG, fg=ACCENT, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(copy, text=title, bg=BG, fg=INK, font=("Segoe UI", 25, "bold")).pack(anchor="w", pady=(4, 2))
        tk.Label(copy, text=subtitle, bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w")
        if action:
            action.pack(side="right", anchor="center")

    def _card(self, parent, padding=16):
        card = ttk.Frame(parent, style="Card.TFrame", padding=padding)
        return card

    def _kpi(self, parent, title, value, note, column):
        card = self._card(parent, 16)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 8 if column < 3 else 0))
        ttk.Label(card, text=title.upper(), style="CardMuted.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=value, style="KpiValue.TLabel").pack(anchor="w", pady=(8, 2))
        ttk.Label(card, text=note, style="CardMuted.TLabel").pack(anchor="w")

    def _build_overview(self):
        actions = tk.Frame(self.main, bg=BG)
        ttk.Button(actions, text="+ Nouvelle campagne", style="Primary.TButton", command=lambda: self.show_view("prospecting")).pack(side="right")
        ttk.Button(actions, text="Actualiser", command=self.load_dashboard).pack(side="right", padx=(0, 10))
        self._page_header("Sales workspace", "Tableau de bord", "Bienvenue Jean Marc, voici l’activité de votre CRM.", actions)
        body = tk.Frame(self.main, bg=BG)
        body.pack(fill="both", expand=True, padx=40, pady=(0, 24))
        kpis = tk.Frame(body, bg=BG)
        kpis.pack(fill="x")
        for index in range(4): kpis.columnconfigure(index, weight=1)
        self.kpi_total = tk.StringVar(value="—")
        self.kpi_pipeline = tk.StringVar(value="—")
        self.kpi_weighted = tk.StringVar(value="—")
        self.kpi_overdue = tk.StringVar(value="—")
        self._kpi(kpis, "Comptes actifs", self.kpi_total, "prospects suivis", 0)
        self._kpi(kpis, "Pipeline ouvert", self.kpi_pipeline, "valeur potentielle", 1)
        self._kpi(kpis, "Pipeline pondéré", self.kpi_weighted, "selon la probabilité", 2)
        self._kpi(kpis, "À traiter", self.kpi_overdue, "relances et tâches en retard", 3)
        middle = tk.Frame(body, bg=BG)
        middle.pack(fill="both", expand=True, pady=(18, 0))
        performance = self._card(middle, 18); performance.pack(side="left", fill="both", expand=True, padx=(0, 9))
        activity = self._card(middle, 18); activity.pack(side="left", fill="both", expand=True, padx=(9, 0))
        performance_head = tk.Frame(performance, bg=CARD); performance_head.pack(fill="x")
        ttk.Label(performance_head, text="Performances", style="CardTitle.TLabel").pack(side="left")
        ttk.Label(performance_head, text="Pipeline réel, pondéré et gagné", style="CardMuted.TLabel").pack(side="left", padx=12)
        self.performance_canvas = tk.Canvas(performance, bg=CARD, highlightthickness=0, height=250)
        self.performance_canvas.pack(fill="both", expand=True, pady=(14, 0))
        ttk.Label(activity, text="Activité récente", style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(activity, text="Les dernières actions de votre équipe.", style="CardMuted.TLabel").pack(anchor="w", pady=(2, 10))
        self.activity_tree = self._tree(activity, [("date", "Date", 110), ("type", "Type", 110), ("account", "Compte", 180), ("content", "Détail", 300)])
        self.activity_tree.configure(height=10)
        self.activity_tree.pack(fill="both", expand=True)
        lower = tk.Frame(body, bg=BG)
        lower.pack(fill="both", expand=True, pady=(18, 0))
        pipeline_card = self._card(lower, 16); pipeline_card.pack(side="left", fill="both", expand=True, padx=(0, 9))
        tasks_card = self._card(lower, 16); tasks_card.pack(side="left", fill="both", expand=True, padx=(9, 0))
        ttk.Label(pipeline_card, text="Pipeline par étape", style="CardTitle.TLabel").pack(anchor="w")
        self.pipeline_tree = self._tree(pipeline_card, [("stage", "Étape", 160), ("count", "Comptes", 90), ("value", "Valeur", 110), ("weighted", "Pondéré", 110)])
        self.pipeline_tree.configure(height=5)
        self.pipeline_tree.pack(fill="both", expand=True, pady=(10, 0))
        ttk.Label(tasks_card, text="Prochaines tâches", style="CardTitle.TLabel").pack(anchor="w")
        self.upcoming_tree = self._tree(tasks_card, [("task", "Tâche", 220), ("account", "Compte", 160), ("due", "Échéance", 100), ("status", "Statut", 100)])
        self.upcoming_tree.configure(height=5)
        self.upcoming_tree.pack(fill="both", expand=True, pady=(10, 0))

    def _draw_performance_chart(self, data):
        if not hasattr(self, "performance_canvas"):
            return
        canvas = self.performance_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 520)
        height = max(canvas.winfo_height(), 230)
        left, top, right, bottom = 42, 18, width - 22, height - 34
        canvas.create_text(left, 2, text="Valeur (€)", anchor="nw", fill=MUTED, font=("Segoe UI", 8))
        for index in range(4):
            y = top + (bottom - top) * index / 3
            canvas.create_line(left, y, right, y, fill="#eef0f6")
            canvas.create_text(left - 8, y, text=str(3 - index), anchor="e", fill=MUTED, font=("Segoe UI", 8))
        kpis = data.get("kpis", {})
        values = [float(kpis.get("pipelineValue", 0) or 0), float(kpis.get("weightedPipeline", 0) or 0), float(kpis.get("wonValue", 0) or 0)]
        maximum = max(values + [1])
        labels = [("Pipeline", ACCENT), ("Pondéré", BLUE), ("Gagné", SUCCESS)]
        bar_width = max(38, (right - left - 60) / 3)
        for index, ((label, color), value) in enumerate(zip(labels, values)):
            x0 = left + 55 + index * (bar_width + 28)
            x1 = x0 + bar_width
            y1 = bottom - (bottom - top) * (value / maximum)
            canvas.create_rectangle(x0, y1, x1, bottom, fill=color, outline="")
            canvas.create_text((x0 + x1) / 2, bottom + 10, text=label, fill=MUTED, font=("Segoe UI", 8))
            canvas.create_text((x0 + x1) / 2, max(y1 - 8, top + 12), text=f"{value:,.0f} €".replace(",", " "), fill=INK, font=("Segoe UI", 9, "bold"))
        canvas.create_text(right, top, text="Mise à jour en direct", anchor="ne", fill=MUTED, font=("Segoe UI", 8))

    def _build_prospects(self):
        new_button = ttk.Button(self.main, text="+ Nouvelle tâche", style="Primary.TButton", command=self.open_task_dialog)
        self._page_header("Comptes & contacts", "Prospects & comptes", "Gérez les entreprises, les contacts, les propriétaires et les relances.", new_button)
        toolbar = self._card(self.main, 12); toolbar.pack(fill="x", padx=30)
        self.crm_query_var = tk.StringVar()
        self.crm_stage_var = tk.StringVar(value="Toutes les étapes")
        self.crm_priority_var = tk.StringVar(value="Toutes les priorités")
        ttk.Label(toolbar, text="Recherche", style="Card.TLabel").pack(side="left")
        ttk.Entry(toolbar, textvariable=self.crm_query_var, width=30).pack(side="left", padx=(8, 14))
        self.crm_stage_combo = ttk.Combobox(toolbar, textvariable=self.crm_stage_var, state="readonly", width=18)
        self.crm_stage_combo.pack(side="left", padx=4)
        self.crm_priority_combo = ttk.Combobox(toolbar, textvariable=self.crm_priority_var, values=["Toutes les priorités", "Haute", "Normale", "Basse"], state="readonly", width=18)
        self.crm_priority_combo.pack(side="left", padx=4)
        self.overdue_var = tk.BooleanVar()
        ttk.Checkbutton(toolbar, text="À relancer", variable=self.overdue_var).pack(side="left", padx=12)
        ttk.Button(toolbar, text="Réinitialiser", command=self.reset_prospect_filters).pack(side="right")
        ttk.Button(toolbar, text="Actualiser", command=self.load_prospects).pack(side="right", padx=8)
        bulkbar = tk.Frame(self.main, bg=BG)
        bulkbar.pack(fill="x", padx=30, pady=(10, 0))
        tk.Label(bulkbar, text="Actions groupées", bg=BG, fg=ACCENT, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 10))
        self.crm_group_var = tk.StringVar(value="Tous les groupes")
        self.crm_group_combo = ttk.Combobox(bulkbar, textvariable=self.crm_group_var, values=["Tous les groupes"] + [self.stage_labels.get(stage, stage) for stage in self.stage_labels], state="readonly", width=20)
        self.crm_group_combo.pack(side="left", padx=(0, 8))
        ttk.Button(bulkbar, text="Sélectionner le groupe", command=self.select_prospect_group).pack(side="left", padx=4)
        ttk.Button(bulkbar, text="Tout sélectionner", command=self.select_all_prospects).pack(side="left", padx=4)
        ttk.Button(bulkbar, text="Désélectionner", command=lambda: self.crm_tree.selection_remove(self.crm_tree.selection())).pack(side="left", padx=4)
        ttk.Button(bulkbar, text="Valider les mails", style="Primary.TButton", command=self.validate_selected_emails).pack(side="right", padx=4)
        ttk.Button(bulkbar, text="Effacer sélection", command=self.delete_selected_prospects).pack(side="right", padx=4)
        card = self._card(self.main, 14); card.pack(fill="both", expand=True, padx=30, pady=(14, 24))
        self.crm_tree = self._tree(card, [("business", "Compte", 240), ("contact", "Contact", 170), ("email", "E-mail", 230), ("stage", "Étape", 130), ("owner", "Propriétaire", 120), ("next", "Prochaine action", 230), ("probability", "%", 65), ("value", "Valeur", 100)], selectmode="extended")
        self.crm_tree.pack(fill="both", expand=True)
        self.crm_tree.bind("<Double-1>", lambda _event: self.open_selected_prospect())
        self.crm_tree.bind("<Delete>", lambda _event: self.delete_selected_prospects())
        bottom = tk.Frame(card, bg=CARD); bottom.pack(fill="x", pady=(12, 0))
        self.crm_summary_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=self.crm_summary_var, style="CardMuted.TLabel").pack(side="left")
        ttk.Button(bottom, text="Tout sélectionner", command=self.select_all_prospects).pack(side="right", padx=4)
        ttk.Button(bottom, text="Sélectionner le groupe", command=self.select_prospect_group).pack(side="right", padx=4)
        ttk.Button(bottom, text="Valider les mails", style="Primary.TButton", command=self.validate_selected_emails).pack(side="right", padx=4)
        ttk.Button(bottom, text="Effacer sélection", command=self.delete_selected_prospects).pack(side="right", padx=4)
        ttk.Button(bottom, text="Ouvrir la fiche", command=self.open_selected_prospect).pack(side="right")
        ttk.Button(bottom, text="Créer brouillon Gmail", command=self.create_gmail_draft).pack(side="right", padx=8)

    def _build_opportunities(self):
        self._page_header("Revenue workspace", "Opportunités", "Suivez les affaires ouvertes, leur probabilité et leur valeur pondérée.")
        toolbar = self._card(self.main, 12); toolbar.pack(fill="x", padx=30)
        self.opportunity_stage_var = tk.StringVar(value="Toutes les étapes ouvertes")
        ttk.Label(toolbar, text="Vue pipeline", style="Card.TLabel").pack(side="left")
        ttk.Combobox(toolbar, textvariable=self.opportunity_stage_var, values=["Toutes les étapes ouvertes"] + [self.stage_labels[s] for s in ["qualified", "contacted", "replied", "meeting", "proposal", "won", "lost"]], state="readonly", width=25).pack(side="left", padx=10)
        ttk.Button(toolbar, text="Actualiser", command=self.load_prospects).pack(side="right")
        cards = tk.Frame(self.main, bg=BG); cards.pack(fill="x", padx=30, pady=14)
        self.opportunity_kpi = tk.StringVar(value="Chargement…")
        ttk.Label(cards, textvariable=self.opportunity_kpi, style="Muted.TLabel").pack(anchor="w")
        card = self._card(self.main, 14); card.pack(fill="both", expand=True, padx=30, pady=(0, 24))
        self.opportunity_tree = self._tree(card, [("business", "Compte", 270), ("stage", "Étape", 140), ("value", "Valeur", 120), ("probability", "Probabilité", 110), ("weighted", "Valeur pondérée", 150), ("close", "Clôture prévue", 130), ("owner", "Propriétaire", 130)])
        self.opportunity_tree.pack(fill="both", expand=True)
        self.opportunity_tree.bind("<Double-1>", lambda _event: self.open_selected_opportunity())

    def _build_tasks(self):
        new_button = ttk.Button(self.main, text="+ Nouvelle tâche", style="Primary.TButton", command=self.open_task_dialog)
        self._page_header("Productivité", "Tâches & activités", "Organisez les relances, appels, rendez-vous et actions internes.", new_button)
        toolbar = self._card(self.main, 12); toolbar.pack(fill="x", padx=30)
        self.task_status_var = tk.StringVar(value="Toutes les tâches")
        self.task_overdue_var = tk.BooleanVar()
        ttk.Label(toolbar, text="Afficher", style="Card.TLabel").pack(side="left")
        ttk.Combobox(toolbar, textvariable=self.task_status_var, values=["Toutes les tâches", "Ouverte", "En cours", "Terminée", "Annulée"], state="readonly", width=18).pack(side="left", padx=10)
        ttk.Checkbutton(toolbar, text="En retard uniquement", variable=self.task_overdue_var, command=self.load_tasks).pack(side="left", padx=10)
        ttk.Button(toolbar, text="Actualiser", command=self.load_tasks).pack(side="right")
        card = self._card(self.main, 14); card.pack(fill="both", expand=True, padx=30, pady=(14, 24))
        self.tasks_tree = self._tree(card, [("title", "Tâche", 340), ("account", "Compte", 250), ("due", "Échéance", 120), ("priority", "Priorité", 110), ("status", "Statut", 120), ("owner", "Propriétaire", 130)])
        self.tasks_tree.pack(fill="both", expand=True)
        self.tasks_tree.bind("<Double-1>", lambda _event: self.toggle_selected_task())
        bottom = tk.Frame(card, bg=CARD); bottom.pack(fill="x", pady=(12, 0))
        self.task_summary_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=self.task_summary_var, style="CardMuted.TLabel").pack(side="left")
        ttk.Button(bottom, text="Marquer comme terminée", command=self.complete_selected_task).pack(side="right")

    def _build_prospecting(self):
        self._page_header("Agent commercial", "Prospection", "Trouvez des prospects puis convertissez-les en comptes suivis.")
        form = self._card(self.main, 14); form.pack(fill="x", padx=30)
        self.region_var = tk.StringVar()
        self.profession_var = tk.StringVar()
        self.custom_profession_var = tk.StringVar()
        self.count_var = tk.StringVar(value="10")
        self._field(form, "Région", self.region_var, 0, 0, 1)
        professions = ["Toutes les activités", "plomberie", "électricité bâtiment", "chauffage climatisation", "menuiserie", "couverture toiture", "entreprise de rénovation", "garage automobile carrosserie", "boulangerie pâtisserie artisanale", "traiteur", "fleuriste", "imprimeur", "cabinet comptable", "agence immobilière", "courtier en assurance", "agence de communication", "consultant entreprise", "grossiste", "commerce avec livraison"]
        ttk.Label(form, text="Profession ciblée", style="Card.TLabel").grid(row=0, column=1, sticky="w", padx=(14, 6))
        ttk.Combobox(form, textvariable=self.profession_var, values=professions, state="readonly", width=27).grid(row=1, column=1, sticky="ew", padx=(14, 6))
        ttk.Label(form, text="Corps de métier libre", style="Card.TLabel").grid(row=0, column=2, sticky="w", padx=6)
        ttk.Entry(form, textvariable=self.custom_profession_var, width=28).grid(row=1, column=2, sticky="ew", padx=6)
        ttk.Label(form, text="Nombre de résultats", style="Card.TLabel").grid(row=0, column=3, sticky="w", padx=6)
        ttk.Combobox(form, textvariable=self.count_var, values=["5", "10", "20"], state="readonly", width=8).grid(row=1, column=3, sticky="w", padx=6)
        ttk.Button(form, text="Rechercher", style="Primary.TButton", command=self.run_search).grid(row=1, column=4, sticky="ew", padx=(14, 0))
        for column in range(5): form.columnconfigure(column, weight=1 if column in (0, 1, 2) else 0)
        card = self._card(self.main, 14); card.pack(fill="both", expand=True, padx=30, pady=(14, 24))
        toolbar = tk.Frame(card, bg=CARD); toolbar.pack(fill="x", pady=(0, 10))
        self.search_count_var = tk.StringVar(value="Aucun résultat")
        ttk.Label(toolbar, textvariable=self.search_count_var, style="CardTitle.TLabel").pack(side="left")
        ttk.Button(toolbar, text="Ajouter la sélection au CRM", command=self.save_selected_result).pack(side="right")
        ttk.Button(toolbar, text="Ajouter toutes les fiches valides", command=self.save_all_results).pack(side="right", padx=8)
        self.results_tree = self._tree(card, [("business", "Entreprise", 250), ("profession", "Métier", 180), ("region", "Région", 130), ("email", "E-mail", 240), ("phone", "Téléphone", 140), ("fit", "Adéquation", 100)])
        self.results_tree.pack(fill="both", expand=True)

    def _field(self, parent, label, variable, row, column, weight):
        ttk.Label(parent, text=label, style="Card.TLabel").grid(row=row, column=column, sticky="w")
        ttk.Entry(parent, textvariable=variable, width=27).grid(row=row + 1, column=column, sticky="ew")
        parent.columnconfigure(column, weight=weight)

    def _tree(self, parent, columns, selectmode="browse"):
        tree = ttk.Treeview(parent, columns=[item[0] for item in columns], show="headings", selectmode=selectmode)
        for key, label, width in columns:
            tree.heading(key, text=label)
            tree.column(key, width=width, minwidth=65, anchor="w")
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        return tree

    def run_async(self, work, success=None):
        self.status_var.set("Traitement en cours…")
        def worker():
            try:
                result = work()
                if success:
                    self.after(0, lambda: success(result))
            except ApiError as error:
                self.after(0, lambda: messagebox.showerror("FÉWURA", str(error)))
            finally:
                self.after(0, lambda: self.status_var.set("Prêt"))
        threading.Thread(target=worker, daemon=True).start()

    def load_dashboard(self):
        self.run_async(lambda: api_request("/api/dashboard"), self.render_dashboard)

    def render_dashboard(self, data):
        self.dashboard = data
        kpis = data.get("kpis", {})
        if hasattr(self, "kpi_total"):
            self.kpi_total.set(str(kpis.get("total", 0)))
            self.kpi_pipeline.set(f"{kpis.get('pipelineValue', 0):,.0f} €".replace(",", " "))
            self.kpi_weighted.set(f"{kpis.get('weightedPipeline', 0):,.0f} €".replace(",", " "))
            self.kpi_overdue.set(str(kpis.get("overdue", 0)))
        self._draw_performance_chart(data)
        self.sidebar_pipeline_var.set(f"{kpis.get('openOpportunities', 0)} opportunités ouvertes\n{ kpis.get('wonValue', 0):,.0f} € gagnés\nTaux de gain : {kpis.get('winRate', 0)} %".replace(",", " "))
        if not hasattr(self, "pipeline_tree"):
            return
        self._clear_tree(self.pipeline_tree)
        for row in data.get("pipeline", []):
            self.pipeline_tree.insert("", "end", values=(self.stage_labels.get(row.get("stage"), row.get("stage")), row.get("count", 0), f"{row.get('value', 0):,.0f} €".replace(",", " "), f"{row.get('weighted_value', 0):,.0f} €".replace(",", " ")))
        self._clear_tree(self.upcoming_tree)
        for task in data.get("tasks", []):
            self.upcoming_tree.insert("", "end", values=(task.get("title", ""), task.get("business_name", "") or "Sans compte", task.get("dueAt", "") or "—", self.task_status_labels.get(task.get("status"), task.get("status", ""))))
        self._clear_tree(self.activity_tree)
        for activity in data.get("activities", []):
            self.activity_tree.insert("", "end", values=(activity.get("created_at", "").replace("T", " ")[:16], activity.get("type", ""), activity.get("business_name", "") or "Sans compte", activity.get("content", "")))

    def load_prospects(self, *_args):
        params = {}
        if hasattr(self, "crm_query_var") and self.crm_query_var.get().strip(): params["q"] = self.crm_query_var.get().strip()
        if hasattr(self, "crm_stage_var") and self.crm_stage_var.get() not in ("", "Toutes les étapes"):
            params["stage"] = next((stage for stage, label in self.stage_labels.items() if label == self.crm_stage_var.get()), "")
        if hasattr(self, "crm_priority_var") and self.crm_priority_var.get() not in ("", "Toutes les priorités"):
            params["priority"] = next((key for key, label in self.priority_labels.items() if label == self.crm_priority_var.get()), "")
        if hasattr(self, "overdue_var") and self.overdue_var.get(): params["overdue"] = "true"
        query = urllib.parse.urlencode(params)
        self.run_async(lambda: api_request(f"/api/prospects?{query}" if query else "/api/prospects"), self.render_prospects)

    def render_prospects(self, data):
        self.prospects = data.get("prospects", [])
        if hasattr(self, "crm_stage_combo"):
            self.crm_stage_combo["values"] = ["Toutes les étapes"] + [self.stage_labels.get(stage, stage) for stage in data.get("stages", [])]
        if hasattr(self, "crm_tree"):
            self._clear_tree(self.crm_tree)
            for index, prospect in enumerate(self.prospects):
                self.crm_tree.insert("", "end", iid=str(index), values=(prospect.get("business_name", ""), prospect.get("contact_name", "") or "—", prospect.get("email", ""), self.stage_labels.get(prospect.get("stage", ""), prospect.get("stage", "")), prospect.get("ownerName", ""), prospect.get("nextAction", "") or "—", f"{prospect.get('probability', 0)} %", f"{prospect.get('dealValue', 0):,.0f} €".replace(",", " ")))
            stats = data.get("stats", {})
            self.crm_summary_var.set(f"{len(self.prospects)} compte(s) affiché(s) · {stats.get('qualified', 0)} opportunité(s) · {stats.get('overdue', 0)} relance(s) en retard")
        if hasattr(self, "opportunity_tree"):
            open_stages = {"qualified", "contacted", "replied", "meeting", "proposal", "won", "lost"}
            opportunities = [prospect for prospect in self.prospects if prospect.get("stage") in open_stages]
            self._clear_tree(self.opportunity_tree)
            for index, prospect in enumerate(opportunities):
                probability = prospect.get("probability", 0)
                value = float(prospect.get("dealValue", 0) or 0)
                self.opportunity_tree.insert("", "end", iid=str(index), values=(prospect.get("business_name", ""), self.stage_labels.get(prospect.get("stage", ""), prospect.get("stage", "")), f"{value:,.0f} €".replace(",", " "), f"{probability} %", f"{value * probability / 100:,.0f} €".replace(",", " "), prospect.get("expectedCloseDate", "") or "—", prospect.get("ownerName", "")))
            total = sum(float(item.get("dealValue", 0) or 0) for item in opportunities)
            weighted = sum(float(item.get("dealValue", 0) or 0) * float(item.get("probability", 0) or 0) / 100 for item in opportunities)
            self.opportunity_kpi.set(f"{len(opportunities)} opportunité(s) · {total:,.0f} € ouverts · {weighted:,.0f} € pondérés".replace(",", " "))

    def load_tasks(self):
        params = {}
        if hasattr(self, "task_status_var") and self.task_status_var.get() != "Toutes les tâches":
            params["status"] = next((key for key, label in self.task_status_labels.items() if label == self.task_status_var.get()), "")
        if hasattr(self, "task_overdue_var") and self.task_overdue_var.get(): params["overdue"] = "true"
        query = urllib.parse.urlencode(params)
        self.run_async(lambda: api_request(f"/api/tasks?{query}" if query else "/api/tasks"), self.render_tasks)

    def render_tasks(self, data):
        self.tasks = data.get("tasks", [])
        self._clear_tree(self.tasks_tree)
        for index, task in enumerate(self.tasks):
            self.tasks_tree.insert("", "end", iid=str(index), values=(task.get("title", ""), task.get("business_name", "") or "Sans compte", task.get("dueAt", "") or "—", self.priority_labels.get(task.get("priority"), task.get("priority", "")), self.task_status_labels.get(task.get("status"), task.get("status", "")), task.get("ownerName", "")))
        open_count = sum(1 for task in self.tasks if task.get("status") in ("open", "in_progress"))
        self.task_summary_var.set(f"{len(self.tasks)} tâche(s) · {open_count} ouverte(s)")

    def run_search(self):
        region = self.region_var.get().strip()
        profession = self.custom_profession_var.get().strip() or self.profession_var.get().strip()
        if not region or not profession:
            messagebox.showwarning("Recherche incomplète", "Saisissez une région et choisissez une activité ou « Toutes les activités ».")
            return
        self.run_async(lambda: api_request("/api/search", "POST", {"region": region, "professions": [profession], "count": self.count_var.get()}), self.render_results)

    def render_results(self, data):
        self.results = data.get("results", [])
        self._clear_tree(self.results_tree)
        for index, result in enumerate(self.results):
            self.results_tree.insert("", "end", iid=str(index), values=(result.get("businessName", ""), result.get("profession", ""), result.get("region", ""), result.get("email", ""), result.get("phone", ""), f"{result.get('fitScore', 0)} pts"))
        self.search_count_var.set(f"{len(self.results)} prospect(s) trouvé(s) · avec e-mail public")

    def save_selected_result(self):
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showinfo("CRM", "Sélectionnez un résultat à ajouter.")
            return
        result = self.results[int(selection[0])]
        self.run_async(lambda: api_request("/api/prospects", "POST", result), lambda _data: (messagebox.showinfo("CRM", "Prospect ajouté au CRM."), self.show_view("prospects")))

    def save_all_results(self):
        if not self.results:
            return messagebox.showinfo("CRM", "Aucun résultat à ajouter.")
        def save_all():
            saved = 0
            for result in self.results:
                try:
                    api_request("/api/prospects", "POST", result)
                    saved += 1
                except ApiError:
                    pass
            return saved
        self.run_async(save_all, lambda saved: (messagebox.showinfo("CRM", f"{saved} prospect(s) ajouté(s) ou mis à jour."), self.show_view("prospects")))

    def selected_prospect(self):
        if not hasattr(self, "crm_tree") or not self.crm_tree.selection(): return None
        return self.prospects[int(self.crm_tree.selection()[0])]

    def selected_prospects(self):
        if not hasattr(self, "crm_tree"): return []
        return [self.prospects[int(item)] for item in self.crm_tree.selection() if str(item).isdigit() and int(item) < len(self.prospects)]

    def select_all_prospects(self):
        if not self.prospects: return messagebox.showinfo("CRM", "Aucun prospect dans la vue actuelle.")
        self.crm_tree.selection_set(*[str(index) for index in range(len(self.prospects))])
        self.status_var.set(f"{len(self.prospects)} prospect(s) sélectionné(s)")

    def select_prospect_group(self):
        if not self.prospects: return messagebox.showinfo("CRM", "Aucun prospect dans la vue actuelle.")
        group_value = self.crm_group_var.get() if hasattr(self, "crm_group_var") else self.crm_stage_var.get()
        selected_stage = next((stage for stage, label in self.stage_labels.items() if label == group_value), "")
        if not selected_stage:
            return self.select_all_prospects()
        ids = [str(index) for index, prospect in enumerate(self.prospects) if prospect.get("stage") == selected_stage]
        if not ids: return messagebox.showinfo("CRM", "Aucun prospect dans ce groupe.")
        self.crm_tree.selection_set(*ids)
        self.status_var.set(f"{len(ids)} prospect(s) du groupe sélectionné(s)")

    def delete_selected_prospects(self):
        selected = self.selected_prospects()
        if not selected: return messagebox.showinfo("CRM", "Sélectionnez au moins un prospect.")
        label = selected[0].get("business_name", "ce prospect") if len(selected) == 1 else f"ces {len(selected)} prospects"
        if not messagebox.askyesno("Effacer les prospects", f"Effacer {label} ?\n\nL’historique et les tâches associés seront aussi supprimés."):
            return
        ids = [prospect.get("id") for prospect in selected]
        self.run_async(lambda: api_request("/api/prospects/bulk-delete", "POST", {"ids": ids}), lambda data: (messagebox.showinfo("CRM", f"{data.get('deleted', len(ids))} prospect(s) effacé(s)."), self.load_prospects()))

    def validate_selected_emails(self):
        selected = self.selected_prospects()
        if not selected: return messagebox.showinfo("Validation des mails", "Sélectionnez au moins un prospect.")
        self.choose_email_offer(selected)

    def choose_email_offer(self, selected):
        dialog = tk.Toplevel(self)
        dialog.title("Choisir l’offre du mail")
        dialog.geometry("510x190")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg=BG)
        tk.Label(dialog, text="Offre mise en avant", bg=BG, fg=INK, font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=20, pady=(18, 8))
        offer_var = tk.StringVar(value="toutes les offres FÉWURA")
        ttk.Combobox(dialog, textvariable=offer_var, state="readonly", width=58, values=("toutes les offres FÉWURA",)).pack(fill="x", padx=20)
        actions = tk.Frame(dialog, bg=BG)
        actions.pack(fill="x", padx=20, pady=18)
        tk.Button(actions, text="Annuler", command=dialog.destroy, bg=CARD, fg=INK, relief="solid", bd=1, padx=12, pady=7).pack(side="right")
        def start_validation():
            offer = offer_var.get().strip()
            dialog.destroy()
            self._validate_selected_emails(selected, offer)
        tk.Button(actions, text="Préparer les mails", command=start_validation, bg=ACCENT, fg="white", relief="flat", padx=12, pady=7).pack(side="right", padx=8)

    def _validate_selected_emails(self, selected, offer):
        def validate():
            success, errors = [], []
            for prospect in selected:
                try:
                    draft = api_request(f"/api/prospects/{prospect['id']}/email", "POST", {"senderName": "Jean Marc", "offer": offer})
                    success.append({"prospect": prospect, "draft": draft})
                except ApiError as error:
                    errors.append({"prospect": prospect, "error": str(error)})
            return success, errors
        def show_result(result):
            success, errors = result
            self.open_email_validation_dialog(selected, success, errors, offer)
            self.load_prospects()
        self.run_async(validate, show_result)

    def open_email_validation_dialog(self, selected, success, errors, offer):
        dialog = tk.Toplevel(self)
        dialog.title("Validation des mails")
        dialog.geometry("920x650")
        dialog.minsize(760, 500)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(bg=BG)
        tk.Label(dialog, text="Validation des mails", bg=BG, fg=INK, font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=20, pady=(18, 2))
        tk.Label(dialog, text=f"{len(success)}/{len(selected)} brouillon(s) généré(s) · Offre : {offer}. Aucun e-mail n’a encore été envoyé.", bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=(0, 12))
        body = tk.Frame(dialog, bg=BG)
        body.pack(fill="both", expand=True, padx=20)
        left = tk.Frame(body, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        left.pack(side="left", fill="y", padx=(0, 12))
        tk.Label(left, text="Messages préparés", bg=CARD, fg=INK, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(12, 6))
        listbox = tk.Listbox(left, width=34, height=22, activestyle="none", selectmode="browse", font=("Segoe UI", 9), relief="flat", borderwidth=0, bg=CARD, fg=INK)
        listbox.pack(side="left", fill="y", padx=(12, 0), pady=(0, 12))
        list_scroll = ttk.Scrollbar(left, orient="vertical", command=listbox.yview)
        list_scroll.pack(side="right", fill="y", padx=(0, 10), pady=(0, 12))
        listbox.configure(yscrollcommand=list_scroll.set)
        items = []
        for item in success:
            prospect, draft = item["prospect"], item["draft"]
            items.append((prospect, draft))
            listbox.insert("end", f"✓ {prospect.get('business_name', '')}")
        for item in errors:
            listbox.insert("end", f"! {item['prospect'].get('business_name', '')}")
        preview_frame = tk.Frame(body, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        preview_frame.pack(side="left", fill="both", expand=True)
        tk.Label(preview_frame, text="Aperçu du mail · Logo FÉWURA intégré", bg=CARD, fg=INK, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "fewura-logo.png")
            dialog.logo_photo = tk.PhotoImage(file=logo_path)
            dialog.logo_photo = dialog.logo_photo.subsample(max(1, dialog.logo_photo.width() // 62), max(1, dialog.logo_photo.height() // 62))
            tk.Label(preview_frame, image=dialog.logo_photo, bg=CARD).pack(anchor="w", padx=14, pady=(0, 6))
        except (tk.TclError, OSError):
            pass
        preview = tk.Text(preview_frame, wrap="word", font=("Segoe UI", 10), bg="#ffffff", fg=INK, relief="flat", padx=14, pady=10)
        preview.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
        preview_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=preview.yview)
        preview_scroll.pack(side="right", fill="y", padx=(0, 12), pady=(0, 12))
        preview.configure(yscrollcommand=preview_scroll.set, state="disabled")

        def show_preview(_event=None):
            index = listbox.curselection()
            if not index: return
            position = index[0]
            if position >= len(items):
                content = errors[position - len(items)]["error"]
            else:
                prospect, draft = items[position]
                phone = prospect.get("phone", "") or "Non renseigné"
                phone_digits = "".join(char for char in phone if char.isdigit())
                whatsapp = f"https://wa.me/{'33' + phone_digits[1:] if phone_digits.startswith('0') and len(phone_digits) == 10 else phone_digits}" if len(phone_digits) >= 8 else "Non disponible"
                content = f"À : {prospect.get('email', 'E-mail non renseigné')}\nObjet : {draft.get('subject', '')}\nTéléphone : {phone}\nWhatsApp : {phone} — {whatsapp}\n\n{draft.get('body', '')}"
            preview.configure(state="normal")
            preview.delete("1.0", "end")
            preview.insert("1.0", content)
            preview.configure(state="disabled")
        listbox.bind("<<ListboxSelect>>", show_preview)
        if items: listbox.selection_set(0); show_preview()

        actions = tk.Frame(dialog, bg=BG)
        actions.pack(fill="x", padx=20, pady=16)
        tk.Button(actions, text="Fermer", command=dialog.destroy, bg=CARD, fg=INK, relief="solid", bd=1, padx=14, pady=8).pack(side="right", padx=(8, 0))
        sendable_ids = [prospect.get("id") for prospect in self.prospects if prospect.get("email") and not prospect.get("optOut") and prospect.get("stage") != "excluded"]
        selected_ids = [item["prospect"].get("id") for item in success]
        def send(ids, label):
            if not ids: return messagebox.showinfo("Envoi des mails", "Aucun e-mail valide à envoyer.", parent=dialog)
            if not messagebox.askyesno("Confirmer l’envoi", f"Envoyer réellement {len(ids)} e-mail(s) ({label}) ?\n\nCette action créera une activité d’envoi dans le CRM.", parent=dialog): return
            dialog.destroy()
            self.run_async(lambda: api_request("/api/prospects/bulk-send-email", "POST", {"ids": ids, "senderName": "Jean Marc", "offer": offer}), lambda data: messagebox.showinfo("Envoi des mails", f"{data.get('sent', 0)}/{data.get('total', len(ids))} e-mail(s) envoyé(s)."))
        tk.Button(actions, text="Envoyer tous les e-mails", command=lambda: send(sendable_ids, "tous les prospects avec e-mail"), bg=ACCENT, fg="white", relief="flat", padx=14, pady=8).pack(side="right", padx=8)
        tk.Button(actions, text="Envoyer la sélection", command=lambda: send(selected_ids, "la sélection"), bg="#16a46a", fg="white", relief="flat", padx=14, pady=8).pack(side="right")

    def open_selected_prospect(self):
        prospect = self.selected_prospect()
        if not prospect:
            return messagebox.showinfo("CRM", "Sélectionnez un compte.")
        self.open_prospect_dialog(prospect)

    def open_selected_opportunity(self):
        if not hasattr(self, "opportunity_tree") or not self.opportunity_tree.selection():
            return messagebox.showinfo("CRM", "Sélectionnez une opportunité.")
        values = self.opportunity_tree.selection()[0]
        open_stages = {"qualified", "contacted", "replied", "meeting", "proposal", "won", "lost"}
        opportunities = [prospect for prospect in self.prospects if prospect.get("stage") in open_stages]
        if int(values) < len(opportunities): self.open_prospect_dialog(opportunities[int(values)])

    def open_prospect_dialog(self, prospect):
        dialog = tk.Toplevel(self)
        dialog.title(f"Compte · {prospect.get('business_name', 'Prospect')}")
        dialog.geometry("780x780")
        dialog.minsize(700, 650)
        dialog.transient(self); dialog.grab_set()
        outer = ttk.Frame(dialog, padding=20); outer.pack(fill="both", expand=True)
        ttk.Label(outer, text=prospect.get("business_name", "Prospect"), style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text=f"{prospect.get('profession', '')} · {prospect.get('region', '')}", style="Muted.TLabel").pack(anchor="w", pady=(2, 12))
        notebook = ttk.Notebook(outer); notebook.pack(fill="both", expand=True)
        info = ttk.Frame(notebook, padding=14); notebook.add(info, text="Fiche compte")
        activity = ttk.Frame(notebook, padding=14); notebook.add(activity, text="Historique")
        fields = {}
        grid = ttk.Frame(info); grid.pack(fill="x")
        definitions = [("contactName", "Contact principal"), ("contactRole", "Fonction"), ("email", "E-mail"), ("phone", "Téléphone"), ("profession", "Secteur / métier"), ("region", "Région"), ("accountType", "Type de compte"), ("leadSource", "Source"), ("ownerName", "Propriétaire"), ("probability", "Probabilité (%)"), ("dealValue", "Valeur estimée (€)"), ("expectedCloseDate", "Clôture prévue (AAAA-MM-JJ)"), ("nextAction", "Prochaine action"), ("nextActionAt", "Échéance de relance")]
        for index, (key, label) in enumerate(definitions):
            row, column = divmod(index, 2)
            ttk.Label(grid, text=label, style="Card.TLabel").grid(row=row * 2, column=column, sticky="w", padx=(0 if column == 0 else 12, 0), pady=(8, 2))
            value = tk.StringVar(value=str(prospect.get(key, "")))
            fields[key] = value
            ttk.Entry(grid, textvariable=value).grid(row=row * 2 + 1, column=column, sticky="ew", padx=(0 if column == 0 else 12, 0))
        grid.columnconfigure(0, weight=1); grid.columnconfigure(1, weight=1)
        stage_var = tk.StringVar(value=prospect.get("stage", "new")); priority_var = tk.StringVar(value=prospect.get("priority", "normal")); optout_var = tk.BooleanVar(value=bool(prospect.get("optOut")))
        controls = ttk.Frame(info); controls.pack(fill="x", pady=(14, 0))
        ttk.Label(controls, text="Étape", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Combobox(controls, textvariable=stage_var, values=list(self.stage_labels.keys()), state="readonly", width=18).grid(row=1, column=0, sticky="ew", padx=(0, 10))
        ttk.Label(controls, text="Priorité", style="Card.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Combobox(controls, textvariable=priority_var, values=["high", "normal", "low"], state="readonly", width=18).grid(row=1, column=1, sticky="ew", padx=(0, 10))
        ttk.Checkbutton(controls, text="Ne plus contacter", variable=optout_var).grid(row=1, column=2, sticky="w")
        controls.columnconfigure(0, weight=1); controls.columnconfigure(1, weight=1)
        ttk.Label(info, text="Notes internes", style="Card.TLabel").pack(anchor="w", pady=(14, 2))
        notes = tk.Text(info, height=6, wrap="word", font=("Segoe UI", 10)); notes.pack(fill="x"); notes.insert("1.0", prospect.get("notes", ""))
        actions = ttk.Frame(info); actions.pack(fill="x", pady=(14, 0))
        def save():
            payload = {key: value.get() for key, value in fields.items()}
            payload.update({"stage": stage_var.get(), "priority": priority_var.get(), "optOut": optout_var.get(), "notes": notes.get("1.0", "end").strip()})
            self.run_async(lambda: api_request(f"/api/prospects/{prospect['id']}", "PATCH", payload), lambda _data: (dialog.destroy(), self.load_prospects()))
        ttk.Button(actions, text="Enregistrer la fiche", style="Primary.TButton", command=save).pack(side="left")
        ttk.Button(actions, text="Créer brouillon Gmail", command=lambda: self.create_gmail_draft_for(prospect)).pack(side="left", padx=8)
        ttk.Button(actions, text="Nouvelle tâche", command=lambda: self.open_task_dialog(prospect)).pack(side="left")
        ttk.Button(actions, text="Fermer", command=dialog.destroy).pack(side="right")
        self.build_activity_tab(activity, prospect)

    def build_activity_tab(self, parent, prospect):
        tree = self._tree(parent, [("date", "Date", 150), ("type", "Type", 130), ("content", "Détail", 420)])
        tree.pack(fill="both", expand=True)
        ttk.Label(parent, text="Ajouter une activité", style="CardTitle.TLabel").pack(anchor="w", pady=(14, 6))
        type_var = tk.StringVar(value="note"); content = tk.Text(parent, height=4, wrap="word", font=("Segoe UI", 10)); content.pack(fill="x")
        ttk.Combobox(parent, textvariable=type_var, values=["note", "call", "email", "meeting", "task"], state="readonly", width=18).pack(anchor="w", pady=7)
        def load():
            try:
                data = api_request(f"/api/prospects/{prospect['id']}/activities")
                self._clear_tree(tree)
                for row in data.get("activities", []): tree.insert("", "end", values=(row.get("created_at", "").replace("T", " ")[:16], row.get("type", ""), row.get("content", "")))
            except ApiError as error: messagebox.showerror("Activité", str(error))
        def add():
            value = content.get("1.0", "end").strip()
            if not value: return messagebox.showinfo("Activité", "Saisissez un détail.")
            self.run_async(lambda: api_request(f"/api/prospects/{prospect['id']}/activities", "POST", {"type": type_var.get(), "content": value}), lambda _data: (content.delete("1.0", "end"), load(), messagebox.showinfo("Activité", "Activité ajoutée.")))
        ttk.Button(parent, text="Ajouter à l’historique", command=add).pack(anchor="e")
        self.run_async(lambda: api_request(f"/api/prospects/{prospect['id']}/activities"), lambda data: [tree.insert("", "end", values=(row.get("created_at", "").replace("T", " ")[:16], row.get("type", ""), row.get("content", ""))) for row in data.get("activities", [])])

    def open_task_dialog(self, prospect=None):
        dialog = tk.Toplevel(self); dialog.title("Nouvelle tâche"); dialog.geometry("520x430"); dialog.transient(self); dialog.grab_set()
        frame = ttk.Frame(dialog, padding=20); frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Créer une tâche", style="Title.TLabel").pack(anchor="w")
        title = tk.StringVar(); due = tk.StringVar(); priority = tk.StringVar(value="normal"); owner = tk.StringVar(value="Jean Marc")
        self._dialog_entry(frame, "Titre", title); self._dialog_entry(frame, "Échéance (AAAA-MM-JJ)", due)
        ttk.Label(frame, text="Priorité").pack(anchor="w", pady=(10, 2)); ttk.Combobox(frame, textvariable=priority, values=["high", "normal", "low"], state="readonly").pack(fill="x")
        ttk.Label(frame, text="Propriétaire").pack(anchor="w", pady=(10, 2)); ttk.Entry(frame, textvariable=owner).pack(fill="x")
        ttk.Label(frame, text="Description").pack(anchor="w", pady=(10, 2)); description = tk.Text(frame, height=5, wrap="word", font=("Segoe UI", 10)); description.pack(fill="both", expand=True)
        def save():
            if not title.get().strip(): return messagebox.showinfo("Tâche", "Le titre est requis.")
            payload = {"title": title.get().strip(), "dueAt": due.get().strip(), "priority": priority.get(), "ownerName": owner.get().strip(), "description": description.get("1.0", "end").strip(), "prospectId": prospect.get("id") if prospect else None}
            self.run_async(lambda: api_request("/api/tasks", "POST", payload), lambda _data: (dialog.destroy(), self.load_tasks() if self.current_view == "tasks" else self.load_dashboard()))
        buttons = ttk.Frame(frame); buttons.pack(fill="x", pady=(12, 0)); ttk.Button(buttons, text="Créer la tâche", style="Primary.TButton", command=save).pack(side="left"); ttk.Button(buttons, text="Annuler", command=dialog.destroy).pack(side="right")

    def _dialog_entry(self, parent, label, variable):
        ttk.Label(parent, text=label).pack(anchor="w", pady=(10, 2)); ttk.Entry(parent, textvariable=variable).pack(fill="x")

    def selected_task(self):
        if not hasattr(self, "tasks_tree") or not self.tasks_tree.selection(): return None
        return self.tasks[int(self.tasks_tree.selection()[0])]

    def complete_selected_task(self):
        task = self.selected_task()
        if not task: return messagebox.showinfo("Tâche", "Sélectionnez une tâche.")
        self.run_async(lambda: api_request(f"/api/tasks/{task['id']}", "PATCH", {"status": "done"}), lambda _data: self.load_tasks())

    def toggle_selected_task(self):
        task = self.selected_task()
        if not task: return
        next_status = "done" if task.get("status") != "done" else "open"
        self.run_async(lambda: api_request(f"/api/tasks/{task['id']}", "PATCH", {"status": next_status}), lambda _data: self.load_tasks())

    def reset_prospect_filters(self):
        self.crm_query_var.set(""); self.crm_stage_var.set("Toutes les étapes"); self.crm_priority_var.set("Toutes les priorités"); self.overdue_var.set(False); self.load_prospects()

    def create_gmail_draft(self):
        prospect = self.selected_prospect()
        if not prospect: return messagebox.showinfo("Gmail", "Sélectionnez un compte avec un e-mail.")
        self.create_gmail_draft_for(prospect)

    def create_gmail_draft_for(self, prospect):
        self.run_async(lambda: api_request(f"/api/prospects/{prospect['id']}/gmail-draft", "POST", {}), lambda data: messagebox.showinfo("Gmail", f"Brouillon créé dans {data.get('account', 'softwareinnovatech@gmail.com')}."))

    def _clear_tree(self, tree):
        for item in tree.get_children(): tree.delete(item)


if __name__ == "__main__":
    FewuraDesktop().mainloop()
