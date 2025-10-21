""" Move Stationary MLC leaves and disable jaw-tracking
Standalone script to apply MLC filtering to every beam in the current RayStation beamset
and display the results.

"""

import logging
import sys

import connect
from BeamOperations import srs_filter_leaves_per_segment


def apply_filter_beams_to_beamset(beamset):
    """
    Apply the `filter_beams` function to every beam in the given beamset.

    Args:
        beamset: A RayStation BeamSet object containing one or more Beam objects.

    Returns:
        Dict[str, str|None]: A mapping from each beam's name to the error message
            returned by `filter_beams`. If filtering was applied successfully,
            the value will be None. If filtering was unnecessary or failed,
            the returned message will describe why.
    """
    results = {}
    for beam in beamset.Beams:
        try:
            error_message = srs_filter_leaves_per_segment(beam)
            results[beam.Name] = error_message
            if error_message:
                logging.debug(f"Beam {beam.Name}: filter_beams returned {error_message}")
            else:
                logging.debug(f"Beam {beam.Name}: filtered successfully or no filtering needed")
        except Exception as e:
            logging.error(f"Exception while filtering beam  {beam.Name}: {e}")
            results[beam.Name] = f"Exception: {e}"
    return results


def main():
    """
    Fetch the current BeamSet, apply filtering, and print results.
    """

    try:
        beamset = connect.get_current("BeamSet")
    except Exception as e:
        logging.error(f"No BeamSet is currently loaded in RayStation. Exiting. {e}")
        sys.exit(1)

    logging.info(f"Applying filter_leaves to all beams in beamset '{beamset.DicomPlanLabel}'...")
    results = apply_filter_beams_to_beamset(beamset)

    # Output put to Execution details
    print("\nFilter Results:")
    print("----------------")
    for name, msg in results.items():
        status = "OK" if msg is None else msg
        print(f"{name}: {status}")


if __name__ == "__main__":
    main()