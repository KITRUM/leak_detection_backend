from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import stumpy
from IPython.display import display
from stumpy import core


# This class includes all functions for the first stage "Univariate pattern and anomaly analysis"
class methane_data:
    """
    Using correspondent number it is easy to call the data from the particular sensor

    """

    datasets = {
        "file": [
            "snorre_19H-QI___2272_10min_(4760).csv",  # 0
            "snorre_19H-QI___2372_10min_(3885).csv",  # 1
            "snorre_19H-QI___2472_10min_(5883).csv",  # 2
            "snorre_19H-QI___4272_10min_(2924).csv",  # 3
            "snorre_19H-QI___5272_10min_(5353).csv",  # 4
            "snorre_19H-QI___5372_10min_(3643).csv",  # 5
            "snorre_19H-QI___5472_10min_(4480).csv",  # 6
            "snorre_19H-QI___6172_10min_(6806).csv",  # 7
            "snorre_19H-QI___6272_10min_(10339).csv",  # 8
            "snorre_19H-QI___6472_10min_(5519).csv",  # 9
            "askeladd_18AIJ012A_10min_(88291).csv",  # 10
            "askeladd_18AIJ012B_10min_(11300).csv",  # 11
            "askeladd_18AIL012A_10min_(16093).csv",  # 12
            "trestakk_1TA_10min_(125810).csv",  # 13
            "trestakk_3TA_10min_(66663).csv",  # 14
            "trestakk_TB_10min_(118209).csv",  # 15
            "troll_TRA-18AI4100A.PV_10min_(1526).csv",  # 16
            "troll_TRA-18AI4100B.PV_10min_(1458).csv",  # 17
            "troll_TRA-18AI4200A.PV_10min_(2019).csv",  # 18
            "troll_TRA-18AI4200B.PV_10min_(6705).csv",  # 19
        ],
        "name": [
            "Snorre 19H-QI___2272",
            "Snorre 19H-QI___2372",
            "Snorre 19H-QI___2472",
            "Snorre 19H-QI___4272",
            "Snorre 19H-QI___5272",
            "Snorre 19H-QI___5372",
            "Snorre 19H-QI___5472",
            "Snorre 19H-QI___6172",
            "Snorre 19H-QI___6272",
            "Snorre 19H-QI___6472",
            "Akeladd 18AIJ012A",
            "Askeladd 18AIJ012B",
            "Askeladd 18AIL012A",
            "Trestakk 1TA",
            "Trestakk 3TA",
            "Trestakk TB",
            "Troll TRA-18AI4100A.PV",
            "Troll TRA-18AI4100B.PV",
            "Troll TRA-18AI4200A.PV",
            "Troll TRA-18AI4200B.PV",
        ],
    }

    def __init__(self, no):
        # to initiate the object we can use number to call precoded names
        if type(no) is int:
            df = pd.read_csv(methane_data.datasets["file"][no], index_col=0)
            df = df = df.loc[df["Values"] < 100000]
            df = df[df["Values"] > 0]
            df["Time"] = pd.to_datetime(df["Time"])
            self.name = methane_data.datasets["name"][no]
            self.values = df.Values.values
            self.time = df.Time.values
            self.df = df
        # we also can initiate the object based on the path of the file with data to analyse
        if type(no) is str:
            df = pd.read_csv(no, index_col=0)
            df = df = df.loc[df["Values"] < 100000]
            df = df[df["Values"] > 0]
            df["Time"] = pd.to_datetime(df["Time"])
            name_l = len(no) - 4
            self.name = no[:name_l]
            self.values = df.Values.values
            self.time = df.Time.values
            self.df = df

    # help tranform dates to readable string
    @staticmethod
    def readable_date(date):
        new_date = datetime.strptime(
            str(date), "%Y-%m-%dT%H:%M:%S.%f000"
        ).strftime("%d.%m.%Y %H:%M")
        return new_date

    # Show all available datasets
    @classmethod
    def show(self):
        data = {"Datasets": self.datasets["name"]}
        cat = pd.DataFrame.from_dict(data)
        display(cat)

    # Plot dataset
    def plot(self):
        plt.title(self.name)
        plt.plot(self.df["Values"])

    @staticmethod
    def stumpy_top_k_discords(T, m, k=1, normalize=False, finite=False):
        """
        This funciton finds the top-k discords of length m with help of matrix profile.

        Parameters
        ---------
        T : numpy.ndarray
            The time series or sequence from which to get the top-k discords

        m : int
            Window size

        k : int
            number of discords to be discovered.

        finite : bool, default False
            If True, subsequence with infinite values will be ignored.

        Returns
        --------
        out : ndarray
            has shape (k, 3). The i-th row cosists of information of i-th discord.
            First column is the discord index. Second column is the distance of discord to its Nearest Neighbor.
            And, third column is the index of discord's NearestNeighbor. The discords are sorted according to their
            distances to their nearest neighbor. If  number of discovered discords is less than k, the remaining rows
            are filled with [-1, np.NINF, -1].

        """
        excl_zone = m

        mp = stumpy.stump(T, m, normalize=normalize)
        P = mp[:, 0].astype(
            np.float64
        )  # change the dtype to np.float64, so it can be used later in core.apply_exclusion_zone

        if finite:
            P[~np.isfinite(P)] = np.NINF

        discords_idx = np.full(k, -1, dtype=np.int64)
        discords_dist = np.full(k, np.NINF, dtype=np.float64)
        discords_nn_idx = np.full(k, -1, dtype=np.int64)

        for i in range(k):
            if np.all(P == np.NINF):
                break
            mp_discord_idx = np.argmax(P)

            discords_idx[i] = mp_discord_idx
            discords_dist[i] = P[mp_discord_idx]
            discords_nn_idx[i] = mp[mp_discord_idx, 1]

            core.apply_exclusion_zone(
                P, discords_idx[i], excl_zone, val=np.NINF
            )

        out = np.empty((k, 3), dtype=object)
        out[:, 0] = discords_idx
        out[:, 1] = discords_dist
        out[:, 2] = discords_nn_idx

        return out

    def find_discords(self, k, steps_list, normalize=False, plot=True):
        """
        This funciton finds the top-k discords of various length by generating diffrent matrix profiles.

        Parameters
        ---------

        k : int
            number of discords for each length to be discovered.

        steps_list: list
            length of discords to be discovered.

        normalize: Boolean
            normalized Matrix Profile

        Returns
        --------
        out : list
            Indicies of dicords found with start and end in tuple

        """

        out = []

        for steps in steps_list:
            dis = self.stumpy_top_k_discords(
                self.values, steps, k=k, normalize=normalize, finite=False
            )
            for num, d in enumerate(dis):
                if d[0] > 1:
                    a = d[0]
                    b = d[0] + steps - 1
                    t1 = self.readable_date(self.time[a])
                    t2 = self.readable_date(self.time[b])
                    out.append((a, b))
                    if plot:
                        plt.title(
                            f"{self.name}: Discord {num+1} ({steps}) {t1} - {t2}"
                        )
                        plt.plot(self.values[a:b])
                        plt.show()
                        print(
                            f"max:{round(max(self.values[a:b]),2)}, min:{round(min(self.values[a:b]),2)}, dissimilarity: {round(d[1],2)}"
                        )

        return out

    def find_motifs(self, k, steps_list, cut=2.0, normalize=True, plot=True):
        """
        This funciton finds the top-k motifs of various length by generating diffrent matrix profiles.

        Parameters
        ---------

        k : int
            number of motifs for each length to be discovered.

        steps_list: list
            length of motifs to be discovered.

        normalize: Boolean
            normalized Matrix Profile

        Returns
        --------
        out : list
            Indicies of motifs found with start and end in tuple

        """

        out = []

        for steps in steps_list:
            mp = stumpy.stump(self.values, m=steps)
            motif_distances, motif_indices = stumpy.motifs(
                self.values,
                mp[:, 0],
                max_motifs=k,
                cutoff=cut,
                min_neighbors=3,
                normalize=normalize,
                max_matches=1000,
            )

            if motif_indices.shape != (1, 0):
                for num, j in enumerate(motif_indices):
                    j = j[j > 0]
                    a = j[0]
                    b = a + steps
                    t1 = self.readable_date(self.time[a])
                    t2 = self.readable_date(self.time[b])
                    out.append((a, b))
                    if plot:
                        plt.title(
                            f"{self.name}: Motif #{num+1} for {steps} steps at Idx:{a} {t1} - {t2}"
                        )
                        for k in j[1:100]:
                            plt.plot(
                                self.values[k : k + steps], c="gray", alpha=0.4
                            )
                        plt.plot(self.values[a:b], c="red")
                        plt.show()

        return out

    def nearest_neighbor(
        self, idx, length, k=2, min_steps=144, sort_by_idx=False
    ):
        """
        This function shows the matches of a motif one by one.

        Parameters
        ---------

        idx : int
            index of motif

        steps_list: list
            length of motif

        sort_by_idx: Boolean
            instead of sorting by similarity, sort matches by distance to motif

        Returns
        --------
        out : list
            Indicies of matches found with start and end in tuple

        """

        out = []
        matches = stumpy.match(
            self.values[idx : idx + length], self.values, max_matches=10000
        )
        m_idxs = []

        for i in matches:
            if abs(idx - i[1]) > min_steps:
                m_idxs.append(i[1])

        idx_dist = []
        if sort_by_idx:
            for i in m_idxs:
                idx_dist.append(abs(idx - i))
            m_idxs = [x for _, x in sorted(zip(idx_dist, m_idxs))]

        maintime = self.time[idx]

        a = idx
        b = a + length
        out.append((a, b))
        t1 = self.readable_date(self.time[a])
        t2 = self.readable_date(self.time[b])
        plt.title(f"{self.name} (Original): idx {a} at {t1} - {t2}")
        plt.plot(self.values[a:b])
        plt.show()

        count = 0

        for a in m_idxs:
            if count >= k:
                break

            b = a + length
            out.append((a, b))

            t1 = self.readable_date(self.time[a])

            t2 = self.readable_date(self.time[b])
            plt.title(f"{self.name}: idx {a} at {t1} - {t2}")
            plt.plot(self.values[a:b])
            plt.show()
            if idx > a:
                timedelta = maintime - self.time[a]
            else:
                timedelta = self.time[a] - maintime
            days = abs(timedelta.astype("timedelta64[D]").astype(np.int32))
            hours = abs(timedelta.astype("timedelta64[h]").astype(np.int32))
            minutes = abs(timedelta.astype("timedelta64[m]").astype(np.int32))
            hours = abs(hours - days * 24)
            minutes = abs(minutes - hours * 60 - days * 24 * 60)
            d_string = ""
            if days == 1:
                d_string = "1 day "
            if days > 1:
                d_string = f"{days} days "
            h_string = ""
            if hours == 1:
                h_string = "1 hour "
            if hours > 1:
                h_string = f"{hours} hours "
            m_string = ""
            if minutes == 1:
                m_string = "1 minute"
            if minutes > 1:
                m_string = f"{minutes} minutes"
            print(f"{d_string}{h_string}{m_string} since the Motif")

            count += 1

        return out

    def find_max_avgs(self, k=5, length=144, exclusion=144, plot=True):
        """
        This function finds subsequences with the highest average values.
        To be used as a comparisson to discords.

        Parameters
        ---------

        k : int
            number of subsequences

        length: int
            length of the sliding window.

        exclusion: int
            the minimum nonoverlaping region for anomalies

        Returns
        --------
        out : list
            Indicies of subsequences found with start and end in tuple

        """
        out = []
        tops = []
        inter = self.values.copy()
        inter = list(inter)
        avgs = []
        idxs = []
        for i, j in enumerate(inter[: len(inter) - length - 1]):
            idxs.append(i)
            a = i
            b = a + length
            avgs.append(sum(inter[a:b]) / length)
        avgs = np.array(avgs)
        ind = np.argpartition(avgs, -k * length)[-k * length :]
        ind_highest = ind[np.argsort(avgs[ind])]
        ind_highest = ind_highest.tolist()
        interval_list = []
        # get intervals
        for idx in ind_highest[::-1]:
            interval_list.append((idx, idx + length))
        interval_list = interval_list.copy()
        # Initialize a stack to hold the non-overlapping intervals.
        non_overlapping_stack = [interval_list[0]]
        interval_list.pop(0)
        while interval_list != []:
            # Iterate through the interval list.
            to_delete = []
            for interval in interval_list:
                ref = non_overlapping_stack[-1]
                # Check if the current interval overlaps with the last interval in the non-overlapping stack.
                if not (
                    (
                        interval[0] < ref[0]
                        and (interval[1] - (length - exclusion)) < ref[0]
                    )
                    or (interval[0] + (length - exclusion) > ref[1])
                ):
                    # If it overlaps add it to the list to delete later
                    to_delete.append(interval)
            # deleting the intervals:
            for interval in to_delete:
                interval_list.remove(interval)
            if interval_list != []:
                non_overlapping_stack.append(interval_list[0])
                interval_list.pop(0)
        out = non_overlapping_stack[:k]
        tops = [avgs[i] for i, _ in out]

        if plot:
            for num, interval in enumerate(out):
                i, j = interval
                t1 = self.time[i]
                t1 = datetime.strptime(
                    str(t1), "%Y-%m-%dT%H:%M:%S.%f000"
                ).strftime("%d.%m.%Y %H:%M")
                t2 = self.time[j]
                t2 = datetime.strptime(
                    str(t2), "%Y-%m-%dT%H:%M:%S.%f000"
                ).strftime("%d.%m.%Y %H:%M")
                plt.title(
                    f"Max average #{num+1} {np.round(tops[num], 2)} {t1} - {t2} "
                )
                plt.plot(self.values[i:j])
                plt.show()

        return out

    def find_max_min_dif(self, k=5, length=144, exclusion=144, plot=True):
        """

        This function finds subsequences with the biggstest difference between its highest and lowest value.
        To be used as a comparisson to find_discords.

        Parameters
        ---------

        k : int
            number of subsequences

        length: int
            length of the sliding window.

        exclusion: int
            the minimum nonoverlaping region for anomalies

        Returns
        --------
        out : list
            Indicies of subsequences found with start and end in tuple

        """
        out = []
        tops = []

        inter = self.values.copy()
        inter = inter.tolist()
        # for m in range(k):
        max_min_difs = []
        idxs = []
        for i, j in enumerate(inter[: len(inter) - length - 1]):
            a = i
            b = a + length
            min_ind = np.argmin(inter[a:b])
            max_ind = np.argmax(inter[a:b])
            if max_ind > min_ind:
                max_min_difs.append(np.max(inter[a:b]) - np.min(inter[a:b]))
            else:
                max_min_difs.append(0.0)
        max_min_difs = np.array(max_min_difs)
        ind = np.argpartition(max_min_difs, -k * length)[-k * length :]
        ind_highest = ind[np.argsort(max_min_difs[ind])]
        ind_highest = ind_highest.tolist()
        interval_list = []
        # get intervals
        for idx in ind_highest[::-1]:
            interval_list.append((idx, idx + length))
        interval_list = interval_list.copy()
        # Initialize a stack to hold the non-overlapping intervals.
        non_overlapping_stack = [interval_list[0]]
        interval_list.pop(0)
        while interval_list != []:
            # Iterate through the interval list.
            to_delete = []
            for interval in interval_list:
                ref = non_overlapping_stack[-1]
                # Check if the current interval overlaps with the last interval in the non-overlapping stack.
                if not (
                    (
                        interval[0] < ref[0]
                        and (interval[1] - (length - exclusion)) < ref[0]
                    )
                    or (interval[0] + (length - exclusion) > ref[1])
                ):
                    # If it overlaps add it to the list to delete later
                    to_delete.append(interval)
            # deleting the intervals:
            for interval in to_delete:
                interval_list.remove(interval)
            if interval_list != []:
                non_overlapping_stack.append(interval_list[0])
                interval_list.pop(0)
        out = non_overlapping_stack[:k]
        tops = [max_min_difs[i] for i, _ in out]
        if plot:
            for num, interval in enumerate(out):
                i, j = interval
                t1 = self.time[i]
                t1 = datetime.strptime(
                    str(t1), "%Y-%m-%dT%H:%M:%S.%f000"
                ).strftime("%d.%m.%Y %H:%M")
                t2 = self.time[j]
                t2 = datetime.strptime(
                    str(t2), "%Y-%m-%dT%H:%M:%S.%f000"
                ).strftime("%d.%m.%Y %H:%M")
                plt.title(
                    f"Max-min difference #{num+1} {np.round(tops[num], 2)} {t1} - {t2} "
                )
                plt.plot(self.values[i:j])
                plt.show()

        return out

    def find_rare_freq(self, k=5, length=144, exclusion=144, average_over=6):
        """

        This function finds anomalies based on the highest powers of frequence intervalls.


        Parameters
        ---------

        k : int
            number of subsequences

        length: int
            length of sliding window.

        exclusion: int
            the minimum nonoverlaping region for anomalies

        average_over: int


        Returns
        --------
        out : list
            Indicies of anomalies found with start and end in tuple

        """

        def get_fft_values(y_values, dt, N, f_s):
            f_values = np.linspace(0.0, 1.0 / (2.0 * dt), N // 2)
            fft_values_ = np.fft.fft(y_values)
            fft_values = 2.0 / N * np.abs(fft_values_[0 : N // 2])
            return f_values, fft_values

        def moving_average(x, w):
            return np.convolve(x, np.ones(w), "valid") / w

        def get_highest_power(time, signal, dt, N):
            fs = 1 / dt
            variance = np.std(signal) ** 2
            f_values, fft_values = get_fft_values(signal, dt, N, fs)
            fft_power = variance * abs(fft_values) ** 2  # FFT power spectrum
            # print(f'the most powerful frequency: {f_values[np.argmax(fft_power)]}')
            ind = np.argpartition(fft_power, -10)[-10:]
            ind_highest = ind[np.argsort(fft_power[ind])]
            n_highest = [f_values[ind] for ind in ind_highest]
            power_of_highest = [fft_power[ind] for ind in ind_highest]
            return n_highest, power_of_highest

        def get_max_power_vec(frequencies, power_spectrum):
            # Create empty lists to store the power spectrum values for each interval
            power_0to08 = []
            power_08to1p5 = []
            power_1p5to2p5 = []
            power_2p5to4p5 = []
            power_4p5toinf = []

            # Loop through each frequency and power spectrum value
            for i in range(len(frequencies)):
                # Determine which interval the frequency falls within and add the corresponding power spectrum value to the appropriate list
                if frequencies[i] >= 0 and frequencies[i] <= 0.8:
                    power_0to08.append(power_spectrum[i])
                elif frequencies[i] > 0.8 and frequencies[i] <= 1.5:
                    power_08to1p5.append(power_spectrum[i])
                elif frequencies[i] > 1.5 and frequencies[i] <= 2.5:
                    power_1p5to2p5.append(power_spectrum[i])
                elif frequencies[i] > 2.5 and frequencies[i] <= 4.5:
                    power_2p5to4p5.append(power_spectrum[i])
                else:
                    power_4p5toinf.append(power_spectrum[i])

            # Determine the highest power spectrum value for each interval
            max_lists = []
            for list_ in [
                power_0to08,
                power_08to1p5,
                power_1p5to2p5,
                power_2p5to4p5,
                power_4p5toinf,
            ]:
                if list_ != []:
                    max_lists.append(max(list_))
                else:
                    max_lists.append(10 ** (-10))
            # Return the highest power spectrum values for each interval
            return max_lists

        def get_power_vec(inter, dt):
            power_vectors_ = []
            for i in range(len(inter) - length - 1):
                a = i
                b = a + length
                signal = moving_average(inter[a:b], average_over)
                N = len(signal)
                time = np.arange(0, N) * dt
                frequencies, power_spectrum = get_highest_power(
                    time, signal, dt, N
                )
                max_power_vec = get_max_power_vec(frequencies, power_spectrum)
                power_vectors_.append(max_power_vec)
            mean_ = np.mean(power_vectors_, axis=0)
            cov = np.cov(power_vectors_, rowvar=False)
            return power_vectors_, mean_, cov

        def get_distance(power_vectors, mean_, cov):
            distances_ = []
            for i, vec in enumerate(power_vectors):
                vec = power_vectors[i]
                distance = np.sqrt(
                    np.dot(
                        np.dot((vec - mean_).T, np.linalg.inv(cov)),
                        vec - mean_,
                    )
                )
                distances_.append(distance)
            distances_ = np.array(distances_)
            return distances_

        def non_overlapping_intervals(interval_list, length, exclusion):
            """
            This function takes a list of tuples with two integers as input,
            representing intervals. It returns a list of intervals that overlap only within allowed zone
            """
            interval_list = interval_list.copy()
            # Initialize a stack to hold the non-overlapping intervals.
            non_overlapping_stack = [interval_list[0]]
            interval_list.pop(0)
            while interval_list != []:
                # Iterate through the interval list.
                to_delete = []
                for interval in interval_list:
                    ref = non_overlapping_stack[-1]
                    # Check if the current interval overlaps with the last interval in the non-overlapping stack.
                    if not (
                        (
                            interval[0] < ref[0]
                            and (interval[1] - (length - exclusion)) < ref[0]
                        )
                        or (interval[0] + (length - exclusion) > ref[1])
                    ):
                        # If it overlaps add it to the list to delete later
                        to_delete.append(interval)
                # deleting the intervals:
                for interval in to_delete:
                    interval_list.remove(interval)
                if interval_list != []:
                    non_overlapping_stack.append(interval_list[0])
                    interval_list.pop(0)
                # print(interval_list)
            return non_overlapping_stack

        out = []
        tops = []
        inter = self.values.copy()
        dt = 1 / 144

        power_vectors, mean_main, cov_main = get_power_vec(inter, dt)
        # Calculate the Mahalanobis distance for each vector
        distances = get_distance(power_vectors, mean_main, cov_main)

        # get more than enough pieces for selection
        ind = np.argpartition(distances, -k * length)[-k * length :]
        ind_highest = ind[np.argsort(distances[ind])]
        ind_highest = ind_highest.tolist()
        intervals = []
        # get intervals
        for idx in ind_highest[::-1]:
            intervals.append((idx, idx + length))
        # get only k non overlapping intervals with highest distances
        out = non_overlapping_intervals(
            intervals, length=length, exclusion=exclusion
        )[:k]
        tops = [distances[i] for i, j in out]

        for i, (e, f) in enumerate(out):
            t1 = self.time[e]
            t1 = datetime.strptime(
                str(t1), "%Y-%m-%dT%H:%M:%S.%f000"
            ).strftime("%d.%m.%Y %H:%M")
            t2 = self.time[f]
            t2 = datetime.strptime(
                str(t2), "%Y-%m-%dT%H:%M:%S.%f000"
            ).strftime("%d.%m.%Y %H:%M")
            # if i % 200 == 0:
            plt.title(
                f"Unusual frequencies #{i+1} {np.round(tops[i], 2)} {t1} - {t2} "
            )
            plt.plot(self.values[e:f])
            plt.show()
        return out

    def deteriorating_motif(self, k, steps, cut=2.0, normalize=False):
        """
        This function shows the motif, its best match, one match from the middle and the worst match.

        Parameters
        ---------

        k : int
            number of subsequences

        stepps: int
            length of motif.

        normalize: Boolean
            z-normalized Matrix Profile

        Returns
        --------
        out : list
            List of Indicies of matches found with start and end in tuple

        """

        out = []

        mp = stumpy.stump(self.values, m=steps)
        motif_distances, motif_indices = stumpy.motifs(
            self.values,
            mp[:, 0],
            max_motifs=10,
            cutoff=cut,
            min_neighbors=3,
            normalize=normalize,
            max_matches=1000,
        )

        motifs = []

        if motif_indices.shape != (1, 0):
            for num, j in enumerate(motif_indices):
                j = j[j > 0]

                a = j[0]
                b = a + steps
                t1 = self.readable_date(self.time[a])
                t2 = self.readable_date(self.time[b])
                middle = len(j[1:]) // 2
                k1 = j[1]
                k2 = j[middle]
                k3 = j[::-1][0]
                plt.title(
                    f"{self.name}: Motif #{num+1} ({steps} steps) at Idx:{a} {t1}"
                )
                plt.plot(self.values[a : a + steps])
                plt.show()
                t1 = self.readable_date(self.time[k1])
                t2 = self.readable_date(self.time[k1 + steps])
                plt.title(
                    f"{self.name}: Motif #{num+1} best Match at idx {k1} {t1}"
                )
                plt.plot(self.values[k1 : k1 + steps])
                plt.show()
                t1 = self.readable_date(self.time[k2])
                t2 = self.readable_date(self.time[k2 + steps])
                plt.title(
                    f"{self.name}: Motif #{num+1} middle Match at idx {k2} {t1}"
                )
                plt.plot(self.values[k2 : k2 + steps])
                plt.show()
                t1 = self.readable_date(self.time[k3])
                t2 = self.readable_date(self.time[k3 + steps])
                plt.title(
                    f"{self.name}: Motif #{num+1} worst Match at idx {k3} {t1}"
                )
                plt.plot(self.values[k3 : k3 + steps])
                plt.show()
                out.append(
                    [
                        (j[0], j[0] + steps),
                        (k1, k1 + steps),
                        (k2, k2 + steps),
                        (k3, k3 + steps),
                    ]
                )
            return out
