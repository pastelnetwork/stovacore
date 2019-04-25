import multiprocessing
import pandas as pd

from ..settings import NetWorkSettings
from .statistics import calculate_spearmans_rho, calculate_kendalls_tau, calculate_bootstrapped_hoeffdings


NUM_WORKERS = int(round(multiprocessing.cpu_count() / 2))


def measure_similarity(combined_fingerprint, fingerprint_table):
    spearman_thresh = NetWorkSettings.DUPE_DETECTION_SPEARMAN_THRESHOLD
    kendall_thresh = NetWorkSettings.DUPE_DETECTION_KENDALL_THRESHOLD
    hoeffding_thresh = NetWorkSettings.DUPE_DETECTION_HOEFFDING_THRESHOLD
    strictness = NetWorkSettings.DUPE_DETECTION_STRICTNESS
    kendall_max = NetWorkSettings.DUPE_DETECTION_KENDALL_MAX
    hoeffding_max = NetWorkSettings.DUPE_DETECTION_HOEFFDING_MAX

    is_duplicate = False

    # prepare combined_fingerprint
    A = pd.DataFrame(["DUMMY_HASH", "DUMMY_PATH"]).T        # TODO: fill these properly?
    B = pd.DataFrame(combined_fingerprint)
    combined_image_fingerprint_df_row = pd.concat([A, B], axis=1, join_axes=[A.index])
    candidate_fingerprint = combined_image_fingerprint_df_row.iloc[:, 2:].T.values.flatten().tolist()
    # end

    print('Checking if candidate image is a likely duplicate of a previously registered artwork:')

    registered_fingerprints = fingerprint_table.iloc[:, 2:].T.values
    print('Comparing candidate image to the fingerprints of %s previously registered images.' % len(fingerprint_table))
    print('Each fingerprint consists of %s numbers.' % len(fingerprint_table.columns))

    # Computing Spearman's Rho, which is fast to compute. We only perform the
    # slower tests on the fingerprints that have a high Rho
    spearman_vector, spearman_max, requires_kendalls = calculate_spearmans_rho(candidate_fingerprint,
                                                                               fingerprint_table,
                                                                               registered_fingerprints,
                                                                               strictness,
                                                                               spearman_thresh)
    print("Computed Spearman's Rho", spearman_max)

    # do we need to calculate Kendall's?
    if len(requires_kendalls) > 0:
        print("Computing Kendall's Tau")
        requires_hoeffdings = calculate_kendalls_tau(candidate_fingerprint, requires_kendalls, strictness, kendall_thresh)

        # do we need to calculate hoeffdings?
        if len(requires_hoeffdings) > 0:
            print("Computing Bootstrapped Hoeffding's")
            duplicates = calculate_bootstrapped_hoeffdings(candidate_fingerprint, spearman_vector, requires_hoeffdings,
                                                           strictness, hoeffding_thresh, NUM_WORKERS)

            # it seems we have found a duplicate
            if len(duplicates):
                is_duplicate = True

                print('WARNING! Art image file appears to be a duplicate!')
                print('Candidate appears to be a duplicate of the image fingerprint beginning with %s' % duplicates[0][0:5])

                for ii in range(len(fingerprint_table)):
                    current_fingerprint = registered_fingerprints[:, ii].tolist()
                    if current_fingerprint == duplicates[0]:
                        shahash = fingerprint_table.iloc[ii, 0]
                        print('The SHA256 hash of the registered artwork that is similar to the candidate image: ' + shahash)

    # assemble parameters
    column_headers = ['spearman_thresh', 'kendall_thresh', 'hoeffding_thresh',
                      'strictness', 'fingerprint_db_size', 'spearman_max',
                      'kendall_max', 'hoeffding_max']
    params_df = pd.DataFrame([spearman_thresh, kendall_thresh, hoeffding_thresh, strictness,
                              float(len(fingerprint_table)), spearman_max, kendall_max, hoeffding_max]).T
    params_df.columns = column_headers
    params_df = params_df.T

    return is_duplicate, params_df


def assemble_fingerprints_for_pandas(db):
    df_vectors = pd.DataFrame()
    pandas_fingerprint_table = pd.DataFrame()

    for current_image_file_hash, data in db:
        file_path, combined = data

        df_vectors = df_vectors.append(combined)

        # create dataframe rows for every image
        df_row = pd.DataFrame([current_image_file_hash, file_path]).T
        pandas_fingerprint_table = pandas_fingerprint_table.append(df_row)

    final_pandas_table = pd.concat([pandas_fingerprint_table, df_vectors], axis=1,
                                   join_axes=[pandas_fingerprint_table.index])
    return final_pandas_table
