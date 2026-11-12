import math
import random

from classes.request import Request


class SystemModel:
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

        self.source_intervals = source_intervals or [
            (1.0, 3.0) for _ in range(num_sources)
        ]
        self.device_rates = device_rates or [0.8 for _ in range(num_devices)]

        self.reset()

    def reset(self):
        self.current_time = 0.0
        self.req_counters = [0] * self.num_sources
        self.dropped_counters = [0] * self.num_sources

        self.buffer = [None] * self.buffer_size

        self.devices_busy = [False] * self.num_devices
        self.devices_req = [None] * self.num_devices

        self.device_pointer = 0

        self.active_package_source = None

        self.next_gen_times = []
        for i in range(self.num_sources):
            t = self.gen_uniform(
                self.source_intervals[i][0], self.source_intervals[i][1]
            )
            self.next_gen_times.append(t)

        self.device_release_times = [float("inf")] * self.num_devices

        self.last_action_desc = "Модель инициализирована. Нажмите 'Сделать шаг (Step)'."

    @staticmethod
    def gen_uniform(a: float, b: float) -> float:
        return random.uniform(a, b)

    @staticmethod
    def gen_exp(rate: float) -> float:
        u = max(random.random(), 1e-9)
        return -math.log(u) / rate

    def get_earliest_event(self):
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
        for offset in range(self.num_devices):
            idx = (self.device_pointer + offset) % self.num_devices
            if not self.devices_busy[idx]:
                self.device_pointer = (idx + 1) % self.num_devices
                return idx
        return None

    def pick_from_buffer(self):
        occupied_indices = [i for i, req in enumerate(self.buffer) if req is not None]
        if not occupied_indices:
            return None, None

        if self.active_package_source is not None:
            pkg_candidates = [
                i
                for i in occupied_indices
                if self.buffer[i].source_id == self.active_package_source
            ]
            if pkg_candidates:
                chosen_idx = min(pkg_candidates, key=lambda i: self.buffer[i].gen_time)
                chosen_req = self.buffer[chosen_idx]
                self.buffer[chosen_idx] = None
                return chosen_req, chosen_idx
            else:
                self.active_package_source = None

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
        event_type, event_idx, event_time = self.get_earliest_event()
        self.current_time = event_time

        if event_type == "SOURCE":
            src_id = event_idx + 1
            self.req_counters[event_idx] += 1
            req_num = self.req_counters[event_idx]
            new_req = Request(src_id, req_num, self.current_time)

            dt = self.gen_uniform(
                self.source_intervals[event_idx][0],
                self.source_intervals[event_idx][1],
            )
            self.next_gen_times[event_idx] = self.current_time + dt

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

            empty_idx = next((i for i, r in enumerate(self.buffer) if r is None), None)
            if empty_idx is not None:
                self.buffer[empty_idx] = new_req
                self.last_action_desc = (
                    f"[{self.current_time:.3f}] Все приборы заняты. Заявка {new_req} "
                    f"поставлена на свободное место #{empty_idx + 1} буфера."
                )
                return

            max_source_in_buf = max(r.source_id for r in self.buffer)
            if new_req.source_id >= max_source_in_buf:
                self.dropped_counters[event_idx] += 1
                self.last_action_desc = (
                    f"[{self.current_time:.3f}] Буфер полон! Заявка {new_req} "
                    f"получила отказ (наименьший приоритет среди буфера)."
                )
            else:
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
