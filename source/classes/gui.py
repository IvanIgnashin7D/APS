import tkinter as tk
from tkinter import messagebox, ttk

from classes.system import SystemModel


class StepModeGUI:
    """Графический интерфейс пошагового режима (ОД1)."""

    def __init__(self, root):
        self.root = root
        self.root.title("СМО: Вариант 10 — Пошаговый режим (Метод особых состояний)")
        self.root.geometry("980x740")

        self.model = SystemModel(num_sources=3, num_devices=3, buffer_size=5)

        self._build_ui()
        self._update_display()

    def _build_ui(self):
        # Панель управления параметрами
        param_frame = ttk.LabelFrame(
            self.root, text="Параметры конфигурации", padding=10
        )
        param_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(param_frame, text="Источников:").grid(row=0, column=0, padx=5)
        self.ent_sources = ttk.Entry(param_frame, width=5)
        self.ent_sources.insert(0, "3")
        self.ent_sources.grid(row=0, column=1, padx=5)

        ttk.Label(param_frame, text="Приборов:").grid(row=0, column=2, padx=5)
        self.ent_devices = ttk.Entry(param_frame, width=5)
        self.ent_devices.insert(0, "3")
        self.ent_devices.grid(row=0, column=3, padx=5)

        ttk.Label(param_frame, text="Емкость буфера:").grid(row=0, column=4, padx=5)
        self.ent_buffer = ttk.Entry(param_frame, width=5)
        self.ent_buffer.insert(0, "5")
        self.ent_buffer.grid(row=0, column=5, padx=5)

        btn_apply = ttk.Button(
            param_frame, text="Применить и перезапустить", command=self._on_reset
        )
        btn_apply.grid(row=0, column=6, padx=15)

        # Информационная строка
        self.lbl_time = ttk.Label(
            self.root,
            text="Текущее модельное время: 0.000",
            font=("Arial", 11, "bold"),
        )
        self.lbl_time.pack(anchor=tk.W, padx=15, pady=4)

        # Таблица Календаря событий
        cal_frame = ttk.LabelFrame(
            self.root,
            text="Календарь событий и источники (ОД1)",
            padding=10,
        )
        cal_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tree_cal = ttk.Treeview(
            cal_frame,
            columns=("event", "time", "status", "total_gen", "dropped"),
            show="headings",
            height=6,
        )
        self.tree_cal.heading("event", text="Событие / Элемент")
        self.tree_cal.heading("time", text="Время след. события")
        self.tree_cal.heading("status", text="Статус")
        self.tree_cal.heading("total_gen", text="Сгенерировано")
        self.tree_cal.heading("dropped", text="Отказов")

        for col in ("event", "time", "status", "total_gen", "dropped"):
            self.tree_cal.column(col, anchor=tk.CENTER, width=150)
        self.tree_cal.pack(fill=tk.BOTH, expand=True)

        # Состояние буфера и приборов (горизонтальное разделение)
        mid_frame = ttk.Frame(self.root)
        mid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Буфер
        buf_frame = ttk.LabelFrame(
            mid_frame, text="Буферная память (Д1ОЗ3, Д1ОО2)", padding=8
        )
        buf_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.tree_buf = ttk.Treeview(
            buf_frame,
            columns=("pos", "req", "source", "time"),
            show="headings",
            height=6,
        )
        self.tree_buf.heading("pos", text="Позиция")
        self.tree_buf.heading("req", text="Заявка")
        self.tree_buf.heading("source", text="Источник")
        self.tree_buf.heading("time", text="Время генерации")
        for col in ("pos", "req", "source", "time"):
            self.tree_buf.column(col, anchor=tk.CENTER, width=80)
        self.tree_buf.pack(fill=tk.BOTH, expand=True)

        # Приборы
        dev_frame = ttk.LabelFrame(
            mid_frame, text="Приборы-воркеры (Д2П2, Д2Б5)", padding=8
        )
        dev_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        self.tree_dev = ttk.Treeview(
            dev_frame,
            columns=("device", "state", "req", "release_time"),
            show="headings",
            height=6,
        )
        self.tree_dev.heading("device", text="Прибор")
        self.tree_dev.heading("state", text="Состояние")
        self.tree_dev.heading("req", text="Текущая заявка")
        self.tree_dev.heading("release_time", text="Время окончания")
        for col in ("device", "state", "req", "release_time"):
            self.tree_dev.column(col, anchor=tk.CENTER, width=90)
        self.tree_dev.pack(fill=tk.BOTH, expand=True)

        # Лог последнего действия
        log_frame = ttk.LabelFrame(self.root, text="Журнал событий", padding=8)
        log_frame.pack(fill=tk.X, padx=10, pady=5)

        self.lbl_action = ttk.Label(
            log_frame,
            text="",
            foreground="#0b4a8c",
            font=("Arial", 9, "italic"),
            wraplength=920,
        )
        self.lbl_action.pack(anchor=tk.W)

        # Кнопки управления пошаговым выполнением
        ctrl_frame = ttk.Frame(self.root, padding=10)
        ctrl_frame.pack(fill=tk.X, padx=10)

        btn_step = tk.Button(
            ctrl_frame,
            text="Сделать шаг (Step) ▶",
            bg="#2e7d32",
            fg="white",
            font=("Arial", 11, "bold"),
            command=self._on_step,
            padx=15,
            pady=5,
        )
        btn_step.pack(side=tk.LEFT, padx=5)

        btn_step10 = ttk.Button(
            ctrl_frame, text="+10 шагов", command=lambda: self._on_multi_step(10)
        )
        btn_step10.pack(side=tk.LEFT, padx=5)

        btn_reset = ttk.Button(ctrl_frame, text="Сброс (Reset)", command=self._on_reset)
        btn_reset.pack(side=tk.RIGHT, padx=5)

    def _on_step(self):
        self.model.step()
        self._update_display()

    def _on_multi_step(self, count: int):
        for _ in range(count):
            self.model.step()
        self._update_display()

    def _on_reset(self):
        try:
            n_src = int(self.ent_sources.get())
            n_dev = int(self.ent_devices.get())
            buf_sz = int(self.ent_buffer.get())
            if n_src <= 0 or n_dev <= 0 or buf_sz <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Ошибка", "Параметры должны быть положительными целыми числами."
            )
            return

        self.model = SystemModel(
            num_sources=n_src, num_devices=n_dev, buffer_size=buf_sz
        )
        self._update_display()

    def _update_display(self):
        self.lbl_time.config(
            text=f"Текущее модельное время: {self.model.current_time:.3f} | "
            f"Указатель прибора (Д2П2): П{self.model.device_pointer + 1} | "
            f"Активный пакет (Д2Б5): {'И' + str(self.model.active_package_source) if self.model.active_package_source else 'нет'}"
        )
        self.lbl_action.config(text=self.model.last_action_desc)

        # Обновление календаря событий
        for item in self.tree_cal.get_children():
            self.tree_cal.delete(item)

        for i in range(self.model.num_sources):
            self.tree_cal.insert(
                "",
                tk.END,
                values=(
                    f"И{i + 1}",
                    f"{self.model.next_gen_times[i]:.3f}",
                    "Генерация",
                    self.model.req_counters[i],
                    self.model.dropped_counters[i],
                ),
            )

        # Обновление буфера
        for item in self.tree_buf.get_children():
            self.tree_buf.delete(item)

        for idx, req in enumerate(self.model.buffer):
            if req is None:
                self.tree_buf.insert("", tk.END, values=(f"#{idx + 1}", "—", "—", "—"))
            else:
                self.tree_buf.insert(
                    "",
                    tk.END,
                    values=(
                        f"#{idx + 1}",
                        f"И{req.source_id}.{req.req_number}",
                        f"И{req.source_id}",
                        f"{req.gen_time:.3f}",
                    ),
                )

        # Обновление приборов
        for item in self.tree_dev.get_children():
            self.tree_dev.delete(item)

        for i in range(self.model.num_devices):
            busy = self.model.devices_busy[i]
            req = self.model.devices_req[i]
            rel_t = self.model.device_release_times[i]
            state_str = "Занят" if busy else "Свободен"
            req_str = f"И{req.source_id}.{req.req_number}" if req else "—"
            rel_str = f"{rel_t:.3f}" if busy else "—"

            self.tree_dev.insert(
                "", tk.END, values=(f"П{i + 1}", state_str, req_str, rel_str)
            )
