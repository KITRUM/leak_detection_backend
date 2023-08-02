import copy

import matplotlib.pyplot as plt
import numpy as np
import stumpy


class sensor_stream:
    border = []

    def __init__(self, ts_array, m, start_stop_list):
        self.initial = ts_array
        self.ts_complete = ts_array
        self.ts = ts_array
        # the algorithm for incremental matrix profile analysis:
        self.stream = stumpy.stumpi(ts_array, m, egress=False, normalize=False)
        self.stream_backup = copy.deepcopy(self.stream)
        # to get max dissimilarity in the baseline
        self.max_dis = max(self.stream.P_)
        self.m = m
        self.discord_per = np.array([])
        self.counter = 0
        ###New variables for feedback:
        self.global_counter = -1  # to track indices for stop and start
        self.start_stop_list = start_stop_list
        self.start_stop_list_backup = copy.deepcopy(self.start_stop_list)
        self.ts_fb = np.array([])  # ts for storage of the feedbacks
        self.fb_temp = np.array([])  # ts for recording of the current feedback
        self.ts_procedure = ts_array  #
        self.max_dis_fb = (
            self.max_dis
        )  # new max dist that works only for feedbacks
        self.stream_fb = copy.deepcopy(self.stream)
        self.stream_fb_backup = copy.deepcopy(self.stream)
        self.start_stop = start_stop_list  # the list

    # updating the baseline till the threshold is reached, then one window is left, the rest is reset
    def track_data(self, datapoint, threshold=288):
        if self.start_stop_list != []:
            # Part relevant for procedure:
            if self.global_counter == self.start_stop_list[0][0]:
                self.ts_procedure = np.append(
                    self.ts_fb, self.ts
                )  # later we need to smooth it to deal with the break points!!!
                self.stream_fb = stumpy.stumpi(
                    self.ts_procedure, self.m, egress=False, normalize=False
                )
            # during the procedure:
            if (
                self.start_stop_list[0][0]
                < self.global_counter
                < self.start_stop_list[0][1]
            ):
                if self.counter > threshold:
                    self.stream_fb = copy.deepcopy(self.stream_fb_backup)
                    self.ts_procedure = copy.deepcopy(
                        np.append(self.ts_fb, self.initial)
                    )
                    self.counter = 0
                    overlap = self.ts_complete[-144:].copy()
                    for i in overlap:
                        self.stream_fb.update(i)
                        self.ts_procedure = np.append(self.ts_procedure, i)
                # recording feedback:
                self.fb_temp = np.append(self.fb_temp, datapoint)
                # anomaly detection:
                self.ts_procedure = np.append(self.ts_procedure, datapoint)
                self.ts_complete = np.append(self.ts_complete, datapoint)
                self.stream_fb.update(datapoint)
                idx = len(self.ts_procedure) - self.m
                dis = self.stream_fb.P_[idx]
                dis_lvl = dis / self.max_dis_fb * 100
                self.discord_per = np.append(self.discord_per, dis_lvl)
                self.counter += 1
                self.global_counter += 1
                return

            if self.global_counter == self.start_stop_list[0][1]:
                # updating feedback time series:
                self.ts_fb = np.append(self.ts_fb, self.fb_temp)
                # preparing for new feedback recording:
                self.fb_temp = np.array([])
                # initiating new reference distance for procedures:
                ts_fb_init = np.append(self.ts_fb, self.initial)
                self.stream_fb = stumpy.stumpi(
                    ts_fb_init, self.m, egress=False, normalize=False
                )
                self.stream_fb_backup = copy.deepcopy(self.stream_fb)
                self.max_dis_fb = max(self.stream_fb.P_)
                self.start_stop_list.pop(0)
                self.ts = copy.deepcopy(self.initial)
                self.counter = 0
                self.stream = copy.deepcopy(self.stream_backup)
                overlap = self.ts_complete[-144:].copy()
                for i in overlap:
                    self.stream.update(i)
                    self.ts = np.append(self.ts, i)
        # normal part:
        if self.counter > threshold:
            self.stream = copy.deepcopy(self.stream_backup)
            self.ts = copy.deepcopy(self.initial)
            self.counter = 0
            overlap = self.ts_complete[-144:].copy()
            for i in overlap:
                self.stream.update(i)
                self.ts = np.append(self.ts, i)
        self.ts = np.append(self.ts, datapoint)
        self.ts_complete = np.append(self.ts_complete, datapoint)
        self.stream.update(datapoint)
        idx = len(self.ts) - self.m
        dis = self.stream.P_[idx]
        dis_lvl = dis / self.max_dis * 100
        self.discord_per = np.append(self.discord_per, dis_lvl)
        self.counter += 1
        self.global_counter += 1

    def plot(self, yellow=100, red=200, title="Data colored by anomaly score"):
        t = np.arange(0.0, len(self.discord_per), 1)
        s = self.discord_per
        v = self.ts_complete[-len(s) :]

        supper = np.ma.masked_where(s < red, v)
        slower = np.ma.masked_where(s > yellow, v)
        smiddle = np.ma.masked_where((s < yellow) | (s > red), v)

        fig, ax = plt.subplots()
        fig.set_size_inches(15, 5)
        plt.title(title, fontsize="25")

        # Visualization of the procedure:
        for left, right in self.start_stop_list_backup:
            ax.fill_between(
                range(left, right), v[left:right], color="orange", alpha=0.3
            )
            ax.axvline(left, lw=1, linestyle="--", color="grey")
            ax.axvline(right, lw=1, linestyle="--", color="grey")

        ax.set_xlabel("Time", fontsize="15")
        ax.set_ylabel("Methane Concentration", fontsize="15")
        ax.plot(t, slower, color="green", label="OK")
        ax.plot(t, smiddle, color="yellow", label="Warning")
        ax.plot(t, supper, color="red", label="Alert!")
        leg = ax.legend()
        plt.show()
