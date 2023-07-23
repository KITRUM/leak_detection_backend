import numpy as np
from dtw import dtw
from stumpy import mpdist

from .mutual_information import norm_mutual_information

__all__ = ("MultiMetricCorrelation",)


class MultiMetricCorrelation(object):
    _x = None
    _y = []
    _ws = -1
    _mi_index = 0
    _mi_mean = 0.0
    _mi_sigma = 0.0
    _mi_deltad_best = 0.0
    _mpdist_index = 0
    _mpdist_mean = 0.0
    _mpdist_sigma = 0.0
    _mpdist_deltad_best = 0.0
    _dtw_index = 0
    _dtw_mean = 0.0
    _dtw_sigma = 0.0
    _dtw_deltad_best = 0.0
    _verbose = False
    _plot = False
    _benchmark = False

    def __init__(
        self, reference, hypotheses, verbose=False, plot=False, benchmark=False
    ):
        """
        :param reference: the measured ppm/V signal from 'AnomalyDetector'
        :param hypotheses: array of the simulated signalsfrom 'Simulator'
        :return:
        """
        self._x = reference
        self._y = hypotheses
        self._ws = -1
        self._mi_index = 0
        self._mi_mean = 0.0
        self._mi_sigma = 0.0
        self._mi_best = 0.0
        self._mi_deltad_best = 0.0
        self._mi_exceed_sigsqr = False
        self._mpdist_index = 0
        self._mpdist_mean = 0.0
        self._mpdist_sigma = 0.0
        self._mpdist_best = 0.0
        self._mpdist_deltad_best = 0.0
        self._mpdist_exceed_sigsqr = False
        self._dtw_index = 0
        self._dtw_mean = 0.0
        self._dtw_sigma = 0.0
        self._dtw_best = 0.0
        self._dtw_deltad_best = 0.0
        self._dtw_exceed_sigsqr = False
        self._verbose = verbose
        self._plot = plot
        self._benchmark = benchmark

    def compute(self):
        self._run_mi()
        self._run_dtw()
        self._run_mpdist()

    def all_exceed_sigma_squared(self):
        return (
            self._mi_exceed_sigsqr
            and self._dtw_exceed_sigsqr
            and self._mpdist_exceed_sigsqr
        )

    def consensus_exceed_sigma_squared(self):
        consensus_pass = False
        consensus_indices = ("", "")
        check = self._mi_exceed_sigsqr and self._dtw_exceed_sigsqr
        if check:
            consensus_indices = ("mi", "dtw")
            consensus_pass = check
        check = self._dtw_exceed_sigsqr and self._mpdist_exceed_sigsqr
        if check:
            consensus_indices = ("dtw", "mpdist")
            consensus_pass = check
        check = self._mpdist_exceed_sigsqr and self._mi_exceed_sigsqr
        if check:
            consensus_indices = ("mpdist", "mi")
            consensus_pass = check
        return consensus_pass, consensus_indices

    def consensus_index(self):
        indices = np.array(
            [self._mi_index, self._dtw_index, self._mpdist_index],
            dtype=np.int32,
        )
        scores = np.array(
            [self._mi_best, self._dtw_best, self._mpdist_best],
            dtype=np.float64,
        )
        method_index = np.argmax(scores)
        return indices[method_index]

    def consensus_quality(self):
        scores = np.array(
            [self._mi_best, self._dtw_best, self._mpdist_best],
            dtype=np.float64,
        )
        method_index = np.argmax(scores)
        return scores[method_index]

    def range_check(self):
        cap_mi = 2.0 * self._mi_sigma
        q1_mi = min(1.0, self._mi_deltad_best / cap_mi)
        cap_dtw = 2.0 * self._dtw_sigma
        q1_dtw = min(1.0, self._dtw_deltad_best / cap_dtw)
        cap_mpdist = 2.0 * self._mpdist_sigma
        q1_mpdist = min(1.0, self._mpdist_deltad_best / cap_mpdist)
        return q1_mi, q1_dtw, q1_mpdist

    @property
    def leak_index_mat(self) -> dict:
        return {
            "mi": self._mi_index,
            "dtw": self._dtw_index,
            "mpdist": self._mpdist_index,
        }

    def _run_mi(self):
        MIs = []
        for i, hypothesis in enumerate(self._y):
            MIs.append(norm_mutual_information(self._x, hypothesis))
        MIs = np.array(MIs)
        self._mi_index = np.argmin(MIs)
        self._mi_mean = np.mean(MIs)
        self._mi_sigma = np.std(MIs)
        self._mi_best = MIs[self._mi_index]
        self._mi_deltad_best = abs(self._mi_best - self._mi_mean)
        self._mi_exceed_sigsqr = self._mi_deltad_best > self._mi_sigma**2
        if self._verbose:
            print(
                "MI - shape = {}, min = {}, max = {}".format(
                    MIs.shape, np.min(MIs), np.max(MIs)
                )
            )
            print(
                (
                    "MI - best_index = {}, mean = {}, std-dev. = {}, "
                    "delta_best = {}"
                ).format(
                    self._mi_index,
                    self._mi_mean,
                    self._mi_sigma,
                    self._mi_deltad_best,
                )
            )
            print("Mutual information scores: {}".format(MIs))

    def _run_dtw(self):
        dtw_dists = []
        for i, hypothesis in enumerate(self._y):
            dtw_dist = dtw(
                self._x, hypothesis, keep_internals=True, distance_only=True
            ).distance
            dtw_dists.append(dtw_dist)
        dtw_dists = np.array(dtw_dists)
        self._dtw_index = np.argmin(dtw_dists)
        self._dtw_mean = np.mean(dtw_dists)
        self._dtw_sigma = np.std(dtw_dists)
        self._dtw_best = dtw_dists[self._dtw_index]
        self._dtw_deltad_best = abs(self._dtw_best - self._dtw_mean)
        self._dtw_exceed_sigsqr = self._dtw_deltad_best > self._dtw_sigma**2
        if self._verbose:
            print(
                "DTW - shape = {}, min = {}, max = {}".format(
                    dtw_dists.shape, np.min(dtw_dists), np.max(dtw_dists)
                )
            )
            print(
                "DTW - mean = {}, std-dev. = {}".format(
                    self._dtw_mean, self._dtw_sigma
                )
            )
            print(
                (
                    "DTW - best_index = {}, delta_best = {}, "
                    "exceeds barrier = {}"
                ).format(
                    self._dtw_index,
                    self._dtw_deltad_best,
                    self._dtw_exceed_sigsqr,
                )
            )
            print("Dynamic Time Warping scores: {}".format(dtw_dists))

    def _run_mpdist(self):
        if self._ws < 0:
            lens = list()
            lens.append(self._x.shape[0])
            lens.append(self._y.shape[1])
            # for item in self._y:
            #     lens.append(item.shape[0])
            N = np.min(lens)
            self._ws = int(np.sqrt(N)) if N > 15 else N
            if self._verbose:
                print("Matrix profile - window size: {}".format(self._ws))
        mp_dists = []
        for hypothesis in self._y:
            mp_dist = mpdist(self._x, hypothesis, self._ws, normalize=False)
            mp_dists.append(mp_dist)

        mp_dists = np.array(mp_dists)

        self._mpdist_index = np.argmin(mp_dists)
        self._mpdist_mean = np.mean(mp_dists)
        self._mpdist_sigma = np.std(mp_dists)
        self._mpdist_best = mp_dists[self._mpdist_index]
        self._mpdist_deltad_best = abs(self._mpdist_best - self._mpdist_mean)
        self._mpdist_exceed_sigsqr = (
            self._mpdist_deltad_best > self._mpdist_sigma**2
        )

        if self._verbose:
            print(
                "MPdist - shape = {}, min = {}, max = {}".format(
                    mp_dists.shape, np.min(mp_dists), np.max(mp_dists)
                )
            )
            print(
                "MPdist - mean = {}, std-dev. = {}".format(
                    self._mpdist_mean, self._mpdist_sigma
                )
            )
            print(
                (
                    "MPdist - best_index = {}, delta_best = {}, "
                    "exceeds barrier = {}"
                ).format(
                    self._mpdist_index,
                    self._mpdist_deltad_best,
                    self._mpdist_exceed_sigsqr,
                )
            )
            print("Matrix Profile Distance scores: {}".format(mp_dists))
