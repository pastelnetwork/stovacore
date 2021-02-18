"""
Utils for image duplication detection.
"""
import random
import functools
import concurrent.futures

import scipy
import scipy.stats
import numpy as np

from .helpers import Timer
from core_modules.helpers import require_true


def __hoeffd_inner_loop_func(i, R, S):
    # See slow_exact_hoeffdings_d_func for definition of R, S
    Q_i = 1 + sum(np.logical_and(R < R[i], S < S[i]))
    Q_i = Q_i + (1 / 4) * (sum(np.logical_and(R == R[i], S == S[i])) - 1)
    Q_i = Q_i + (1 / 2) * sum(np.logical_and(R == R[i], S < S[i]))
    Q_i = Q_i + (1 / 2) * sum(np.logical_and(R < R[i], S == S[i]))
    return Q_i


def __generate_bootstrap_sample_func(original_length_of_input, sample_size):
    bootstrap_indices = np.array([random.randint(1, original_length_of_input) for x in range(sample_size)])
    return bootstrap_indices


def __compute_average_and_stdev_of_25th_to_75th_percentile_func(input_vector):
    input_vector = np.array(input_vector)
    percentile_25 = np.percentile(input_vector, 25)
    percentile_75 = np.percentile(input_vector, 75)
    trimmed_vector = input_vector[input_vector > percentile_25]
    trimmed_vector = trimmed_vector[trimmed_vector < percentile_75]
    trimmed_vector_avg = np.mean(trimmed_vector)
    trimmed_vector_stdev = np.std(trimmed_vector)
    return trimmed_vector_avg, trimmed_vector_stdev


def __compute_bootstrapped_hoeffdings_d_func(x, y, sample_size):
    x = np.array(x)
    y = np.array(y)
    require_true (x.size == y.size)
    original_length_of_input = x.size
    bootstrap_sample_indices = __generate_bootstrap_sample_func(original_length_of_input - 1, sample_size)
    N = sample_size
    x_bootstrap_sample = x[bootstrap_sample_indices]
    y_bootstrap_sample = y[bootstrap_sample_indices]
    R_bootstrap = scipy.stats.rankdata(x_bootstrap_sample)
    S_bootstrap = scipy.stats.rankdata(y_bootstrap_sample)
    hoeffdingd = functools.partial(__hoeffd_inner_loop_func, R=R_bootstrap, S=S_bootstrap)
    Q_bootstrap = [hoeffdingd(x) for x in range(sample_size)]
    Q = np.array(Q_bootstrap)
    D1 = sum(((Q - 1) * (Q - 2)))
    D2 = sum((R_bootstrap - 1) * (R_bootstrap - 2) * (S_bootstrap - 1) * (S_bootstrap - 2))
    D3 = sum((R_bootstrap - 2) * (S_bootstrap - 2) * (Q - 1))
    D = 30 * ((N - 2) * (N - 3) * D1 + D2 - 2 * (N - 2) * D3) / (N * (N - 1) * (N - 2) * (N - 3) * (N - 4))
    return D


def __apply_bootstrap_hoeffd_func(x, y, sample_size, ii):
    verbose = 0
    if verbose:
        print('Bootstrap ' + str(ii) + ' started...')
    return __compute_bootstrapped_hoeffdings_d_func(x, y, sample_size)


def bootstrapped_hoeffd(x, y, sample_size, number_of_bootstraps, num_workers):
    list_of_Ds = list()
    # TODO: audit whether this can cause problems for us, DoS or otherwise
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        inputs = range(number_of_bootstraps)
        f = functools.partial(__apply_bootstrap_hoeffd_func, x, y, sample_size)
        for result in executor.map(f, inputs):
            list_of_Ds.append(result)

    robust_average_D, robust_stdev_D = __compute_average_and_stdev_of_25th_to_75th_percentile_func(list_of_Ds)
    return robust_average_D


def calculate_spearmans_rho(candidate_fingerprint, fingerprint_table, registered_fingerprints, strictness, threshold):
    with Timer():
        spearman_vector = []
        for i in range(len(fingerprint_table)):
            part = registered_fingerprints[:, i]
            correlation = scipy.stats.spearmanr(candidate_fingerprint, part).correlation
            spearman_vector.append(correlation)

        spearman_max = np.array(spearman_vector).max()

        above_threshold = np.nonzero(np.array(spearman_vector) >= strictness * threshold)[0].tolist()

        percentage = len(above_threshold) / len(spearman_vector)

    print(('Selected %s fingerprints for further testing' +
          '(%.2f%% of the total registered fingerprints).') % (len(above_threshold), round(100 * percentage, 2)))

    futher_testing_needed = [registered_fingerprints[:, current_index].tolist() for current_index in above_threshold]

    spearman_scores = [scipy.stats.spearmanr(candidate_fingerprint, x).correlation for x in futher_testing_needed]
    require_true (all(np.array(spearman_scores) >= strictness * threshold))

    return spearman_vector, spearman_max, futher_testing_needed


def calculate_kendalls_tau(candidate_fingerprint, filtered_fingerprints, strictness, threshold):
    futher_testing_needed = []

    with Timer():
        kendall_vector = []
        for i in filtered_fingerprints:
            correlation = scipy.stats.kendalltau(candidate_fingerprint, i).correlation
            kendall_vector.append(correlation)

        kendall_max = np.array(kendall_vector).max()
        if kendall_max >= strictness * threshold:
            indices = list(np.nonzero(np.array(kendall_vector) >= strictness * threshold)[0])
            futher_testing_needed = [filtered_fingerprints[current_index] for current_index in indices]

    return futher_testing_needed


def calculate_bootstrapped_hoeffdings(candidate_fingerprint,
                                      spearman_vector, filtered_fingerprints, strictness, hoeffding_thresh,
                                      num_workers):
    duplicates = []

    percentage = round(100 * len(filtered_fingerprints) / len(spearman_vector), 2)
    print(('Selected %s fingerprints for further testing' +
           '(%.2f%% of the total registered fingerprints).') % (len(filtered_fingerprints), percentage))

    print('Now computing bootstrapped Hoeffding D for selected fingerprints...')
    sample_size = 80
    number_of_bootstraps = 30

    with Timer():
        print('Sample Size: %s, Number of Bootstraps: %s' % (sample_size, number_of_bootstraps))
        hoeffding_vector = []
        for current_fingerprint in filtered_fingerprints:
            tmp = bootstrapped_hoeffd(candidate_fingerprint, current_fingerprint,
                                      sample_size, number_of_bootstraps, num_workers)
            hoeffding_vector.append(tmp)

        hoeffding_max = np.array(hoeffding_vector).max()
        if hoeffding_max >= strictness * hoeffding_thresh:
            above_threshold = list(np.nonzero(np.array(hoeffding_vector) >= strictness * hoeffding_thresh)[0])
            duplicates = [filtered_fingerprints[current_index] for current_index in above_threshold]

    return duplicates
