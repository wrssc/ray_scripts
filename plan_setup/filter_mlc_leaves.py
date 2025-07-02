""" Filter MLC leaves in all beams of the current RayStation beamset.
Standalone script to apply MLC filtering to every beam in the current RayStation beamset
and display the results.

Usage:
    Place this file in your RayStation scripts folder, then run via the ScriptSelector.
"""

import logging
import sys

import connect
from BeamOperations import srs_filter_leaves


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
            error_message = srs_filter_leaves(beam)
            results[beam.Name] = error_message
            if error_message:
                logging.debug("Beam %s: filter_beams returned '%s'", beam.Name, error_message)
            else:
                logging.debug("Beam %s: filtered successfully or no filtering needed", beam.Name)
        except Exception as exc:
            logging.error("Exception while filtering beam %s: %s", beam.Name, exc)
            results[beam.Name] = f"Exception: {exc}"
    return results


def main():
    """
    Main entry point: fetch the current BeamSet, apply filtering, and print results.
    """

    try:
        beamset = connect.get_current("BeamSet")
    except Exception as e:
        logging.error(f"No BeamSet is currently loaded in RayStation. Exiting. {e}")
        sys.exit(1)

    logging.info(f"Applying filter_leaves to all beams in beamset '{beamset.DicomPlanLabel}'...")
    results = apply_filter_beams_to_beamset(beamset)

    print("\nFilter Results:")
    print("----------------")
    for name, msg in results.items():
        status = "OK" if msg is None else msg
        print(f"{name}: {status}")


if __name__ == "__main__":
    main()