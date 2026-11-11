import math
import random
import tkinter as tk
from tkinter import messagebox, ttk


class Request:
    """Сущность сетевого запроса / заявки."""

    def __init__(self, source_id: int, req_number: int, gen_time: float):
        self.source_id = source_id
        self.req_number = req_number
        self.gen_time = gen_time

    def __repr__(self):
        return f"И{self.source_id}.{self.req_number}"


class SystemModel:
    """Имитационная модель СМО (Вариант 10, пошаговый режим)."""

    def __init__(
        self,
        num_sources=3,
        num_devices=3,
        buffer_size=5,
        source_intervals=None,
        device_rates=None,
    ):
        self.num_sources = num_sources
        self.num_devices = num_devices
        self.buffer_size = buffer_size

        # Параметры генерации [A, B] для равномерного закона (ИЗ2)
        self.source_intervals = source_intervals or [
            (1.0, 3.0) for _ in range(num_sources)
        ]
        # Параметры интенсивности lambda для экспоненциального закона (ПЗ1)
        self.device_rates = device_rates or [0.8 for _ in range(num_devices)]

        self.reset()

    def reset(self):
        self.current_time = 0.0
        self.req_counters = [0] * self.num_sources
        self.dropped_counters = [0] * self.num_sources

        # Буфер фиксированной емкости (ячейки 0..buffer_size-1), Д1ОЗ3
        self.buffer = [None] * self.buffer_size

        # Приборы: статус и текущая заявка
        self.devices_busy = [False] * self.num_devices
        self.devices_req = [None] * self.num_devices

        # Указатель выбора прибора по кольцу (Д2П2)
        self.device_pointer = 0

        # Активный пакет источников для обслуживания (Д2Б5)
        self.active_package_source = None

        # Календарь будущих событий:
        # события источников (время генерации следующей заявки)
        self.next_gen_times = []
        for i in range(self.num_sources):
            t = self.gen_uniform(
                self.source_intervals[i][0], self.source_intervals[i][1]
            )
            self.next_gen_times.append(t)

        # события приборов (время завершения обслуживания, inf если свободен)
        self.device_release_times = [float("inf")] * self.num_devices

        self.last_action_desc = "Модель инициализирована. Нажмите 'Сделать шаг (Step)'."

    @staticmethod
    def gen_uniform(a: float, b: float) -> float:
        return random.uniform(a, b)

    @staticmethod
    def gen_exp(rate: float) -> float:
        # Экспоненциальное время обслуживания: -ln(U) / lambda
        u = max(random.random(), 1e-9)
        return -math.log(u) / rate

    def get_earliest_event(self):
        """Определяет ближайшее особое событие."""
        min_src_idx = min(range(self.num_sources), key=lambda i: self.next_gen_times[i])
        min_src_time = self.next_gen_times[min_src_idx]

        min_dev_idx = min(
            range(self.num_devices), key=lambda i: self.device_release_times[i]
        )
        min_dev_time = self.device_release_times[min_dev_idx]

        if min_src_time <= min_dev_time:
            return ("SOURCE", min_src_idx, min_src_time)
        return ("DEVICE", min_dev_idx, min_dev_time)

    def find_free_device_round_robin(self):
        """Поиск свободного прибора по кольцу (Д2П2)."""
        for offset in range(self.num_devices):
            idx = (self.device_pointer + offset) % self.num_devices
            if not self.devices_busy[idx]:
                self.device_pointer = (idx + 1) % self.num_devices
                return idx
        return None

    def pick_from_buffer(self):
        """Выбор заявки из буфера пакетами по источнику (Д2Б5)."""
        occupied_indices = [i for i, req in enumerate(self.buffer) if req is not None]
        if not occupied_indices:
            return None, None

        # Проверка, есть ли еще заявки активного пакета в буфере
        if self.active_package_source is not None:
            pkg_candidates = [
                i
                for i in occupied_indices
                if self.buffer[i].source_id == self.active_package_source
            ]
            if pkg_candidates:
                # Внутри пакета берем заявку, пришедшую раньше всех (FIFO)
                chosen_idx = min(pkg_candidates, key=lambda i: self.buffer[i].gen_time)
                chosen_req = self.buffer[chosen_idx]
                self.buffer[chosen_idx] = None
                return chosen_req, chosen_idx
            else:
                self.active_package_source = None

        # Выбираем новый пакет с наивысшим приоритетом (меньший ID источника)
        sources_in_buf = sorted({self.buffer[i].source_id for i in occupied_indices})
        best_source = sources_in_buf[0]
        self.active_package_source = best_source

        pkg_candidates = [
            i for i in occupied_indices if self.buffer[i].source_id == best_source
        ]
        chosen_idx = min(pkg_candidates, key=lambda i: self.buffer[i].gen_time)
        chosen_req = self.buffer[chosen_idx]
        self.buffer[chosen_idx] = None
        return chosen_req, chosen_idx

    def step(self):
        """Совершает один шаг имитации по календарю особых событий."""
        event_type, event_idx, event_time = self.get_earliest_event()
        self.current_time = event_time

        if event_type == "SOURCE":
            src_id = event_idx + 1
            self.req_counters[event_idx] += 1
            req_num = self.req_counters[event_idx]
            new_req = Request(src_id, req_num, self.current_time)

            # Планируем следующее поступление от этого источника
            dt = self.gen_uniform(
                self.source_intervals[event_idx][0],
                self.source_intervals[event_idx][1],
            )
            self.next_gen_times[event_idx] = self.current_time + dt

            # 1. Проверяем свободные приборы
            free_dev = self.find_free_device_round_robin()
            if free_dev is not None:
                self.devices_busy[free_dev] = True
                self.devices_req[free_dev] = new_req
                serv_time = self.gen_exp(self.device_rates[free_dev])
                self.device_release_times[free_dev] = self.current_time + serv_time
                self.last_action_desc = (
                    f"[{self.current_time:.3f}] Источник И{src_id} сгенерировал заявку {new_req}. "
                    f"Назначена на свободный прибор П{free_dev + 1} (освободится в {self.device_release_times[free_dev]:.3f})."
                )
                return

            # 2. Если все приборы заняты, пытаемся поставить в буфер (Д1ОЗ3)
            empty_idx = next((i for i, r in enumerate(self.buffer) if r is None), None)
            if empty_idx is not None:
                self.buffer[empty_idx] = new_req
                self.last_action_desc = (
                    f"[{self.current_time:.3f}] Все приборы заняты. Заявка {new_req} "
                    f"поставлена на свободное место #{empty_idx + 1} буфера."
                )
                return

            # 3. Буфер переполнен: дисциплина отказа Д1ОО2 (по приоритету источника)
            # Худший приоритет = максимальный номер источника
            max_source_in_buf = max(r.source_id for r in self.buffer)
            if new_req.source_id >= max_source_in_buf:
                # Новая заявка имеет такой же или худший приоритет — отказ ей самой
                self.dropped_counters[event_idx] += 1
                self.last_action_desc = (
                    f"[{self.current_time:.3f}] Буфер полон! Заявка {new_req} "
                    f"получила отказ (наименьший приоритет среди буфера)."
                )
            else:
                # Выбиваем наименее приоритетную из буфера (при равенстве — самую старую)
                candidates = [
                    i
                    for i, r in enumerate(self.buffer)
                    if r.source_id == max_source_in_buf
                ]
                evict_idx = min(candidates, key=lambda i: self.buffer[i].gen_time)
                dropped_req = self.buffer[evict_idx]
                self.dropped_counters[dropped_req.source_id - 1] += 1

                self.buffer[evict_idx] = new_req
                self.last_action_desc = (
                    f"[{self.current_time:.3f}] Буфер полон! Заявка {new_req} выбила "
                    f"заявку {dropped_req} из ячейки #{evict_idx + 1} (Д1ОО2)."
                )

        elif event_type == "DEVICE":
            dev_idx = event_idx
            finished_req = self.devices_req[dev_idx]
            self.devices_busy[dev_idx] = False
            self.devices_req[dev_idx] = None
            self.device_release_times[dev_idx] = float("inf")

            # Проверяем буфер на наличие очереди (Д2Б5)
            next_req, buf_idx = self.pick_from_buffer()
            if next_req is not None:
                self.devices_busy[dev_idx] = True
                self.devices_req[dev_idx] = next_req
                serv_time = self.gen_exp(self.device_rates[dev_idx])
                self.device_release_times[dev_idx] = self.current_time + serv_time
                self.last_action_desc = (
                    f"[{self.current_time:.3f}] Прибор П{dev_idx + 1} завершил обработку {finished_req}. "
                    f"Взята заявка {next_req} из буфера (пакет И{next_req.source_id}, ячейка #{buf_idx + 1})."
                )
            else:
                self.last_action_desc = (
                    f"[{self.current_time:.3f}] Прибор П{dev_idx + 1} завершил обработку {finished_req}. "
                    f"Буфер пуст, прибор перешел в режим ожидания."
                )


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


if __name__ == "__main__":
    app_root = tk.Tk()
    gui = StepModeGUI(app_root)
    app_root.mainloop()
