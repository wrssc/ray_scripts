""" Perform structure operations on Raystation plans

	exclude_from_export
	toggles the rois export status

	check_roi
	checks if an ROI has contours

	exists_roi
	checks if ROI is present in the contour list

	max_roi
	checks for maximum extent of an roi

	Versions:
	01.00.00 Original submission

	Known Issues:

	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by the
	Free Software Foundation, either version 3 of the License, or (at your
	option) any later version.

	This program is distributed in the hope that it will be useful, but
	WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
	or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
	for more details.

	You should have received a copy of the GNU General Public License along
	with this program. If not, see <http://www.gnu.org/licenses/>.
	"""

__author__ = "Adam Bayliss"
__contact__ = "rabayliss@wisc.edu"
__date__ = "2020-03-20"

__version__ = "1.0.0"
__status__ = "Production"
__deprecated__ = False
__reviewer__ = "Adam Bayliss"

__reviewed__ = ""
__raystation__ = "8.0.SPB"
__maintainer__ = "Adam Bayliss"

__email__ = "rabayliss@wisc.edu"
__license__ = "GPLv3"
__help__ = ''
__copyright__ = "Copyright (C) 2018, University of Wisconsin Board of Regents"

from GeneralOperations import logcrit as logcrit
import UserInterface
import System.Drawing
import logging
import os
import sys
import connect
import clr
import re
import copy
import numpy as np
import pandas as pd
import xml

clr.AddReference("System.Drawing")


def exclude_from_export(case, rois):
	"""Toggle export
	:param case: current case
	:param rois: name of structure to exclude"""

	if type(rois) is not list:
		rois = [rois]

	try:
		case.PatientModel.ToggleExcludeFromExport(
			ExcludeFromExport=True, RegionOfInterests=rois, PointsOfInterests=[]
		)
	except Exception:
		logging.warning("Unable to exclude {} from export".format(rois))


def include_in_export(case, rois):
	"""Toggle export to true
	:param case: current case
	:param rois: name of structure to exclude"""

	if type(rois) is not list:
		rois = [rois]

	defined_rois = []
	for r in case.PatientModel.RegionsOfInterest:
		defined_rois.append(r.Name)

	for r in defined_rois:
		if r in rois:
			try:
				case.PatientModel.ToggleExcludeFromExport(
					ExcludeFromExport=False, RegionOfInterests=r, PointsOfInterests=[]
				)

			except Exception:
				logging.warning("Unable to include {} in export".format(rois))
		else:
			try:
				case.PatientModel.ToggleExcludeFromExport(
					ExcludeFromExport=True, RegionOfInterests=r, PointsOfInterests=[]
				)

			except Exception:
				logging.warning("Unable to exclude {} from export".format(rois))


def exists_roi(case, rois):
	"""See if rois is in the list"""
	if type(rois) is not list:
		rois = [rois]

	defined_rois = []
	for r in case.PatientModel.RegionsOfInterest:
		defined_rois.append(r.Name)

	roi_exists = []

	for r in rois:
		pattern = r"^" + r + "$"
		if any(re.match(pattern, current_roi, re.IGNORECASE) for current_roi in defined_rois):
			roi_exists.append(True)
		else:
			roi_exists.append(False)

	return roi_exists


def exists_poi(case, pois):
	"""See if rois is in the list"""
	if type(pois) is not list:
		pois = [pois]

	defined_pois = []
	for p in case.PatientModel.PointsOfInterest:
		defined_pois.append(p.Name)

	poi_exists = []

	for p in pois:
		i = 0
		exact_match = False
		if p in defined_pois:
			while i < len(defined_pois):
				if p == defined_pois[i]:
					logging.debug("{} is an exact match to {}".format(p, defined_pois[i]))
					exact_match = True
				i += 1
			if exact_match:
				poi_exists.append(True)
			else:
				poi_exists.append(False)
		else:
			poi_exists.append(False)

	return poi_exists


def has_coordinates_poi(case, exam, poi):
	"""See if pois have locations
	Currently this script will simply look to see if the coordinates are
	finite.

	:param case: desired RS case object from connect
	:param exam: desired RS exam object from connect
	:param poi: type(str) of an existing point of interest name

	TODO Accept an optional ROI as an input, if we have one, then
		Add a bounding box check using:
			case.PatientModel.StructureSets[exam.Name].RoiGeometries['External'].GetBoundingBox
	Usage:
		import StructureOperations
		test = StructureOperations.has_coordinates_poi(
			case=case, exam=exam, poi='SimFiducials')
	"""

	poi_position = case.PatientModel.StructureSets[exam.Name].PoiGeometries[poi]
	test_points = [
		abs(poi_position.Point.x) < 1e5,
		abs(poi_position.Point.y) < 1e5,
		abs(poi_position.Point.z < 1e5),
	]
	if all(test_points):
		return True
	else:
		return False


def check_roi(case, exam, rois):
	""" See if the provided rois has contours, later check for contiguous"""
	if type(rois) is not list:
		rois = [rois]

	roi_passes = []

	if all(exists_roi(case=case, rois=rois)):

		for r in rois:
			if case.PatientModel.StructureSets[exam.Name].RoiGeometries[r].HasContours():
				roi_passes.append(True)
			else:
				roi_passes.append(False)

		return roi_passes

	else:

		return [False]


def max_coordinates(case, exam, rois):
	"""
	Returns the maximum coordinates of the rois as a nested dictionary, e.g.
	rois = PTV1
	a = max_coordinates(case=case, exam=exam, rois=rois)
	a['PTV1']['min_x'] = ...

	TODO: Give max Patient L/R/A/P/S/I, and consider creating a type with
	defined methods
	"""
	if type(rois) is not list:
		rois = [rois]

	if any(exists_roi(case, rois)):
		logging.warning(
			"Maximum Coordinates of ROI: {}".format(rois)
			+ "could NOT be determined. ROI does not exist"
		)
		return None

	logging.debug("Determining maximum coordinates of ROI: {}".format(rois))

	ret = (
		case.PatientModel.StructureSets[exam.Name]
			.RoiGeometries[rois]
			.SetRepresentation(Representation="Contours")
	)
	logging.debug("ret of operation is {}".format(ret))

	max_roi = {}

	for r in rois:
		x = []
		y = []
		z = []

		contours = case.PatientModel.StructureSets[exam].RoiGeometries[rois].PrimaryShape.Contours

		for contour in contours:
			for point in contour:
				x.append(point.x)
				y.append(point.y)
				z.append(point.z)

		max_roi[r] = {
			"min_x": min(x),
			"max_x": max(x),
			"max_y": min(y),
			"min_y": max(y),
			"min_z": min(z),
			"max_z": max(z),
		}
		return max_roi


def define_sys_color(rgb):
	""" Takes an rgb list and converts to a Color object useable by RS
	:param rgb: an rgb color list, e.g. [128, 132, 256]
	:return Color object"""

	return System.Drawing.Color.FromArgb(255, rgb[0], rgb[1], rgb[2])


def change_roi_color(case, roi_name, rgb):
	"""
	Change the color of an roi to a system color
	:param case: RS case object
	:param roi_name: string containing name of roi to be checked
	:param rgb: an rgb color object, e.g. [r, g, b] = [128, 132,256]
	:return error_message: None for success, or error message for error
	"""
	if not all(exists_roi(case=case, rois=roi_name)):
		error_message = "Structure {} not found on case {}".format(roi_name, case)
		return error_message
	# Convert rgb list to system color
	sys_rgb = define_sys_color(rgb)
	try:
		rs_roi = case.PatientModel.RegionsOfInterest[roi_name]
		rs_roi.Color = sys_rgb
		error_message = None
	except:
		error_message = "Unable to change color on roi {}".format(roi_name)
	return error_message

def change_roi_type(case, roi_name, roi_type):
	"""
	:param case: RS Case object
	:param roi_name: string containing roi name to be changed
	:param roi_type: type of roi to be changed to. Available types include:
	Avoidance -> OrganAtRisk
	Bolus -> Other
	BrachyAccessory -> Unknown
	BrachyChannel -> Unknown
	BrachyChannelShield -> Unknown
	BrachySourceApplicator -> Unknown
	Cavity -> Unknown
	ContrastAgent -> Unknown
	Control -> Unknown
	CTV -> Target
	DoseRegion -> Unknown
	External -> OrganAtRisk
	FieldOfView -> Unknown
	Fixation -> Other
	GTV -> Target
	IrradiatedVolume -> Unknown
	Marker -> Unknown
	Organ -> OrganAtRisk
	PTV -> Target
	Registration -> Unknown
	Support -> Other
	TreatedVolume -> Unknown
	Undefined -> Unknown
	:return error_message: None for success and error message for error
	"""
	other_types = ["Fixation", "Support"]
	organ_types = ["Avoidance", "Organ"]
	target_types = ["Ctv", "Gtv", "Ptv"]
	unknown_types = ["BrachyAccessory", "BrachyChannel", "BrachyChannelShield",
					 "BrachySourceApplicator", "Cavity", "ContrastAgent",
					 "Control", "DoseRegion", "FieldOfView",
					 "IrradiatedVolume", "Marker", "Registration",
					 "TreatedVolume", "Undefined"]
	if not all(exists_roi(case=case, rois=roi_name)):
		error_message = "Structure {} not found on case {}".format(roi_name, case)
		return error_message
	try:
		rs_roi = case.PatientModel.RegionsOfInterest[roi_name]
		rs_roi.Type = roi_type
		if any(roi_type in types for types in other_types):
			rs_roi.OrganData.OrganType = "Other"
		elif any(roi_type in types for types in organ_types):
			rs_roi.OrganData.OrganType = "OrganAtRisk"
		elif any(roi_type in types for types in target_types):
			rs_roi.OrganData.OrganType = "Target"
		elif any(roi_type in types for types in unknown_types):
			rs_roi.OrganData.OrganType = "Unknown"
		error_message = None
	except:
	   error_message = "Unable to change type on roi {}".format(roi_name)
	return error_message


def find_targets(case):
	"""
	Find all structures with type 'Target' within the current case.
	Return the matches as a list
	:param case: Current RS Case
	:return: plan_targets # A List of targets
	"""

	# Find RS targets
	plan_targets = []
	for r in case.PatientModel.RegionsOfInterest:
		if r.OrganData.OrganType == "Target":
			plan_targets.append(r.Name)
	# Add user threat: empty PTV list.
	if not plan_targets:
		connect.await_user_input(
			"The target list is empty." + " Please apply type PTV to the targets and continue."
		)
		for r in case.PatientModel.RegionsOfInterest:
			if r.OrganData.OrganType == "Target":
				plan_targets.append(r.Name)
	if plan_targets:
		return plan_targets
	else:
		sys.exit("Script cancelled")


def case_insensitive_structure_search(case, structure_name, roi_list=None):
	"""
	Check if a case insensitive match to the structure_name exists and
	return the name or None
	:param case: raystation case
	:param structure_name:structure name to be tested
	:param roi_list: list of rois to look in, if not specified, use all rois
	:return: name as defined in RayStation, or None if no match was found.
	"""
	# If no roi_list is given, build it using all roi in the case
	if roi_list is None:
		roi_list = []
		for s in case.PatientModel.StructureSets:
			for r in s.RoiGeometries:
				if r.OfRoi.Name not in roi_list:
					roi_list.append(r.OfRoi.Name)

	for current_roi in roi_list:
		if re.search(r'^' + structure_name + '$', current_roi, re.IGNORECASE):
			if not re.search(r'^' + structure_name + '$', current_roi):
				return current_roi
	return None


def exams_containing_roi(case, structure_name, roi_list=None, exam=None):
	"""
		See if structure has contours on this exam, if no exam is supplied
		search all examinations in the case
		Verify if a structure with the exact name specified exists or not
		:param case: Current RS case
		:param structure_name: the name of the structure to be confirmed
		:param roi_list: a list of available ROI's as RS RoiGeometries to
						 check against
		:return: roi_found list of exam names (keys) in which roi has contours
	"""
	# If no roi_list is given, build it using all roi in the case
	if roi_list is None:
		roi_list = []
		for s in case.PatientModel.StructureSets:
			for r in s.RoiGeometries:
				if r not in roi_list:
					roi_list.append(r)
	# If no exam is supplied build a list of all examination names
	exam_list = []
	if exam == None:
		for e in case.Examinations:
			exam_list.append(e.Name)
	else:
		exam_list = [exam]

	roi_found = []

	if any(roi.OfRoi.Name == structure_name for roi in roi_list):
		for e in exam_list:
			e_has_contours = (
				case.PatientModel.StructureSets[e].RoiGeometries[structure_name].HasContours()
			)
			if e_has_contours:
				roi_found.append(e)
	return roi_found


def check_structure_exists(case, structure_name, roi_list=None, option="Check", exam=None):
	"""
	Verify if a structure with the exact name specified exists or not
	:param case: Current RS case
	:param structure_name: the name of the structure to be confirmed
	:param roi_list: a list of available ROIs as RS RoiGeometries to check
					 against
	:param option: desired behavior
		Delete - deletes structure if found
		Check - simply returns true or false if found
		Wait - prompt user to create structure if not found
	:param exam: Current RS exam, if supplied the script deletes geometry only,
				 otherwise contour is deleted
	:return: Logical - True if structure is present in ROI List,
					   False otherwise
	"""

	# If no roi_list is given, build it using all roi in the case
	if roi_list is None:
		roi_list = []
		for s in case.PatientModel.StructureSets:
			for r in s.RoiGeometries:
				if r not in roi_list:
					roi_list.append(r)

	if any(roi.OfRoi.Name == structure_name for roi in roi_list):
		if exam is not None:
			structure_has_contours_on_exam = (
				case.PatientModel.StructureSets[exam.Name]
					.RoiGeometries[structure_name]
					.HasContours()
			)
		else:
			structure_has_contours_on_exam = False

		if option == "Delete":
			if structure_has_contours_on_exam:
				case.PatientModel \
					.StructureSets[exam.Name] \
					.RoiGeometries[structure_name] \
					.DeleteGeometry()
				logging.warning(structure_name + " found - deleting geometry")
				return False
			else:
				case.PatientModel.RegionsOfInterest[structure_name].DeleteRoi()
				logging.warning(structure_name + " found - deleting and creating")
				return True
		elif option == "Check":
			if exam is not None and structure_has_contours_on_exam:
				# logging.info(
				#     "Structure {} has contours on exam {}".format(structure_name, exam.Name)
				# )
				return True
			elif exam is not None:
				# logging.info(
				#     "Structure {} has no contours on exam {}".format(structure_name, exam.Name)
				# )
				return False
			else:
				# logging.info("Structure {} exists in this Case {}"
				#              .format(structure_name, case.Name)
				# )
				return True
		elif option == "Wait":
			if structure_has_contours_on_exam:
				logging.info(
					"Structure {} has contours on exam {}".format(structure_name, exam.Name)
				)
				return True
			else:
				logging.info(
					"Structure {} not found on exam {}, prompted user to create".format(
						structure_name, exam.Name
					)
				)
				connect.await_user_input(
					"Create the structure {} and continue script.".format(structure_name)
				)
	else:
		logging.info(structure_name + " not found")
		return False


def convert_poi(poi1):
	"""
	Return a poi as a numpy array
	:param poi1:
	:return: poi_arr
	"""

	poi_arr = np.array([poi1.Point.x, poi1.Point.y, poi1.Point.z])
	return poi_arr


def check_overlap(patient, case, exam, structure, rois):
	"""
	Checks the overlap of structure with the roi list defined in rois.
	Returns the volume of overlap
	:param: patient: RS patient object
	:param exam: RS exam object
	:param case: RS Case object
	:param structure: List of target structures for overlap
	:param rois: List of structures which will be checked for overlap with structure
	:return: vol
	"""
	exist_list = exists_roi(case, rois)
	roi_index = 0
	rois_verified = []
	# Check all incoming rois to see if they exist in the list
	for r in exist_list:
		if r:
			rois_verified.append(rois[roi_index])
		roi_index += 1
	logging.debug(
		"Found the following in evaluation of overlap with {}: ".format(structure, rois_verified)
	)

	overlap_name = "z_overlap"
	for r in structure:
		overlap_name += "_" + r

	overlap_defs = {
		"StructureName": overlap_name,
		"ExcludeFromExport": True,
		"VisualizeStructure": False,
		"StructColor": [ 192, 192, 192],
		"OperationA": "Union",
		"SourcesA": structure,
		"MarginTypeA": "Expand",
		"ExpA": [0] * 6,
		"OperationB": "Union",
		"SourcesB": rois_verified,
		"MarginTypeB": "Expand",
		"ExpB": [0] * 6,
		"OperationResult": "Intersection",
		"MarginTypeR": "Expand",
		"ExpR": [0] * 6,
		"StructType": "Undefined",
	}
	make_boolean_structure(patient=patient, case=case, examination=exam, **overlap_defs)
	vol = None
	try:
		t = case.PatientModel.StructureSets[exam.Name].RoiGeometries[overlap_name]
		if t.HasContours():
			vol = t.GetRoiVolume()
		else:
			logging.info("{} has no contours, index undefined".format(overlap_name))
	except:
		logging.warning("Error getting volume for {}, volume => 0.0".format(overlap_name))

	logging.debug("Calculated volume of overlap of {} is {}".format(overlap_name, vol))
	case.PatientModel.RegionsOfInterest[overlap_name].DeleteRoi()
	return vol


def find_types(case, roi_type=None):
	"""
	Return a list of all structures that in exist in the roi list with type roi_type
	:param patient:
	:param case:
	:param exam:
	:param type:
	:return: found_roi
	"""
	found_roi = []
	for r in case.PatientModel.RegionsOfInterest:
		if not roi_type:
			found_roi.append(r.Name)
		elif r.Type == roi_type:
			found_roi.append(r.Name)
	return found_roi


def translate_roi(case, exam, roi, shifts):
	"""
	Translate (only) an roi according to the shifts
	:param case:
	:param exam:
	:param roi:
	:param shifts: a dictionary containing shifts, e.g.
		shifts = {'x': 1.0, 'y':1.0, 'z':1.0} would shift in each direction 1 cm
	:return: centroid of shifted roi
	"""
	x = shifts["x"]
	y = shifts["y"]
	z = shifts["z"]
	transform_matrix = {
		"M11": 1, "M12": 0, "M13": 0, "M14": x,
  		"M21": 0, "M22": 1, "M23": 0, "M24": y,
		"M31": 0, "M32": 0, "M33": 1, "M34": z,
		"M41": 0, "M42": 0, "M43": 0, "M44": 1,
	}
	case.PatientModel.RegionsOfInterest["TomoCouch"].TransformROI3D(
		Examination=exam, TransformationMatrix=transform_matrix
	)
	# case.PatientModel.StructureSets[exam].RoiGeometries[roi].TransformROI3D(
	#    Examination=exam,TransformationMatrix=transform_matrix)


def levenshtein_match(item, arr, num_matches=None):
	"""[match,dist]=__levenshtein_match(item,arr)"""

	# Initialize return args
	if num_matches is None:
		num_matches = 1

	dist = [max(len(item), min(map(len, arr)))] * num_matches
	match = [None] * num_matches

	# Loop through array of options
	for a in arr:
		v0 = range(len(a) + 1) + [0]
		v1 = [0] * len(v0)
		for b in range(len(item)):
			v1[0] = b + 1
			for c in range(len(a)):
				if item[b].lower() == a[c].lower():
					v1[c + 1] = min(v0[c + 1] + 1, v1[c] + 1, v0[c])

				else:
					v1[c + 1] = min(v0[c + 1] + 1, v1[c] + 1, v0[c] + 1)

			v0, v1 = v1, v0

		for i, d in enumerate(dist):
			if v0[len(a)] < d:
				dist.insert(i, v0[len(a)])
				dist.pop()
				match.insert(i, a)
				match.pop()
				break

	return match, dist


def find_normal_structures_match(rois, standard_rois, num_matches=None):
	"""
	Return a unique structure dictionary from supplied element tree
	:param rois: a list of rois to be matched
	:param standard_rois: a dict keyed by the rois standard name with an unsorted list of aliases
	:param num_matches: the number of matches to return
	:return: matched_rois : a dict of form { Roi1: [Exact match, Close match, ...], where
							exact match and close match are determined by Levenshtein distance or
							aliases (previously determined synonyms) for this structure
	"""
	match_threshold = 0.6  # Levenshtein match distance
	# If the number of matches to return is not specified, then return the best match
	if num_matches is None:
		num_matches = 1

	standard_names = []
	aliases = {}
	for n, a in standard_rois.items():
		standard_names.append(n)
		if a is not None:
			aliases[n] = a
	matched_rois = {}  # return variable described above
	# alias_distance
	#   An arbitrary number < 1 meant to indicate a distance match that is better
	#   than the levenshtein because it is an alias
	alias_distance = 0.001
	for r in rois:
		[match, dist] = levenshtein_match(r, standard_names, num_matches)
		matched_rois[r] = []
		# unsorted_matches
		#   Dict object: {Key: [(Match distance, Match name),
		#                       (Match distance, MatchName2),
		#                       ... num_matches}
		unsorted_matches = []
		# Create an ordered list. If there is an exact match,
		# make the first element in the ordered list that.
		re_ci_r = re.compile(r,re.IGNORECASE)
		for a_key, a_val in aliases.items():
			for v in a_val:
				if re.match(re_ci_r, v):
					unsorted_matches.append((alias_distance, a_key))
		for i, d in enumerate(dist):
			if d < len(r) * match_threshold:
				# Return Criteria
				lr_mismatch = False
				# Continue checking the current elements in the match list if there is not already
				# an entry for this organ in our output
				if match[i] not in matched_rois[r]:
					# If the structure has a laterality indication,
					#   don't return results that contain the opposite laterality
					if "_L" in match[i] and ("_R" in r or "R_" in r):
						lr_mismatch = True
					if "_R" in match[i] and ("_L" in r or "L_" in r):
						lr_mismatch = True
					if not lr_mismatch:
						unsorted_matches.append((d, match[i]))
		sorted_matches = sorted(unsorted_matches, key=lambda m: m[0])
		# If the aliasing and matching produced nothing, then
		# add a blank element to the beginning of the sorted list
		if not sorted_matches:
			sorted_matches.append((0, ""))
		elif sorted_matches[0][0] > alias_distance:
			sorted_matches.insert(0, (0, ""))
		matched_rois[r] = sorted_matches

	return matched_rois


def filter_rois(plan_rois, skip_targets=True, skip_planning=True):
	"""
	Filters the plan rois for structures that may not need matching and eliminates duplicates
	:param plan_rois:
	:param skip_targets:
	:param skip_planning:
	:return: filtered_rois
	"""
	# Regex expressions for targets
	target_expressions = ["^PTV", "^ITV", "^GTV", "^CTV"]
	# Regex expressions for planning structs
	planning_expressions = [
		"^OTV",
		"^sOTV",
		"^opt",
		"^sPTV",
		"_EZ_",
		"^ring",
		"_PTV[0-9]",
		"^Ring",
		"^Normal",
		"^OAR_PTV",
		"^IGRT",
		"^AllPTV",
		"^InnerAir",
		"z_derived",
		"Uniform",
		"Underdose",
	]
	regex_list = []
	if skip_targets:
		regex_list.extend(target_expressions)
	if skip_planning:
		regex_list.extend(planning_expressions)
	# Given the above arguments, filter the list using the regex and return the result
	filtered_rois = []
	for r in plan_rois:
		filter_roi = False
		for exp in regex_list:
			if re.match(exp, r):
				filter_roi = True
		if r not in filtered_rois and not filter_roi:
			filtered_rois.append(r)
	return filtered_rois


def match_dialog(matches, elements,df_rois=None):
	"""
	Dialog for matching taking the matches found in the search and
	pairing them with protocol elements
	:param matches: matched elements in the form {PlanROI: <Matched_Protocol ROI>}
	:param elements: Elementtree list of roi elements
	:return: dialog_result:
							{'CopyOfReplace':<'Copy' or 'Replace'>,
							PlanROI: <Matching ROI subelement>, or
							a string indicating a user-typed input}
	"""
	# Make dialog inputs
	inputs = {}
	initial = {}
	datatype = {}
	options = {}
	# First element
	k_copy = "0"
	inputs[k_copy] = "Structures that cannot be renamed should have suffix, e.g. (_R or _A):"
	initial[k_copy] = "_R"
	datatype[k_copy] = "text"
	for k, v in matches.iteritems():
		inputs[k] = k
		datatype[k] = "combo"
		options[k] = [x[1] for x in v]
		initial[k] = v[0][1]

	matchy_dialog = UserInterface.InputDialog(
		inputs=inputs,
		title="Matchy Matchy",
		datatype=datatype,
		initial=initial,
		options=options,
		required=[k_copy],
	)
	# Launch the dialog
	response = matchy_dialog.show()
	if response == {}:
		logging.info("create_objective cancelled by user")
		sys.exit("create_objective cancelled by user")
	# Parse the responses
	dialog_result = {}
	# Figure out if we are copying or renaming.
	dialog_result["Suffix"] = response[k_copy]
	df_matches =  {}
	for r, m in response.iteritems():
		# Manage responses
		if r != k_copy:
			# Change the name of r to m
			if not m:
				dialog_result[r] = None
			else:
				if df_rois is not None:
					df_e = df_rois[df_rois.name == m]
					# If more than one result is returned by the dataframe search report an error
					if len(df_e) > 1:
						logging.warning('Too many matching {}. That makes me a sad panda. :('.format(m))
					elif df_e.empty:
						logging.debug('{} was not found in the protocol list'.format(m))
						found_index = None
					else:
						df_matches[m] = df_e
						e_name = df_e.name.values[0]
						found_index = df_e.index
				else:
					for e_index, standard_rois in enumerate(elements):
						if standard_rois.find("name").text == m:
							found_index = e_index
							break
						else:
							found_index = None
				if found_index is not None:
					if df_rois is None:
						logging.debug(
							"Found element match {}: returning element {}".format(
							r, elements[found_index].find("name").text
							)
						)
						dialog_result[r] = elements[found_index]
					else:
						dialog_result[r] = df_e
				# Address user supplied contour
				else:
					logging.debug("No element match {}: returning string {}".format(r, m))
					dialog_result[r] = m
	return dialog_result


def iter_standard_rois(etree):
	"""
	Load the contents of a roi object from xml into a pandas dataframe
	:param etree:
	:return: rois
	"""
	rois = {"rois": []}
	for r in etree.iter('roi'):
		roi = {}
		try:
			roi["name"] = r.find('name').text
		except AttributeError:
			roi["name"] = None
		try:
			roi["TG263PrimaryName"] = r.find('TG263PrimaryName').text
		except AttributeError:
			roi["TG263PrimaryName"] = None
		try:
			roi["Description"] = r.find('Description').text
		except AttributeError:
			roi["Description"] = None
		try:
			roi["TargetType"] = r.find('TargetType').text
		except AttributeError:
			roi["TargetType"] = None
		try:
			roi["RTROIInterpretedType"] = str(r.find('RTROIInterpretedType').text).capitalize()
		except AttributeError:
			roi["RTROIInterpretedType"] = None
		try:
			roi["MajorCategory"] = r.find('MajorCategory').text
		except AttributeError:
			roi["MajorCategory"] = None
		try:
			roi["MinorCategory"] = r.find('MinorCategory').text
		except AttributeError:
			roi["MinorCategory"] = None
		try:
			roi["AnatomicGroup"] = r.find('AnatomicGroup').text
		except AttributeError:
			roi["AnatomicGroup"] = None
		try:
			roi["NCharacters"] = r.find('NCharacters').text
		except AttributeError:
			roi["NCharacters"] = None
		try:
			roi["TG263ReverseOrderName"] = r.find('TG263ReverseOrderName').text
		except AttributeError:
			roi["TG263ReverseOrderName"] = None
		try:
			roi["FMAID"] = r.find('FMAID').text
		except AttributeError:
			roi["FMAID"] = None
		try:
			roi["Color"] = r.find('Color').text
			# RGBColor will be a list of [r, g, b], it gets converted using 
			# [r, g, b] : [int(x) for x in df_e.RGBColor.values[0]]
			if roi["Color"] is not None:
				roi["RGBColor"] = [r.find("Color").attrib["red"],
								   r.find("Color").attrib["green"],
								   r.find("Color").attrib["blue"]]
			else:
				roi["RGBColor"] = None
		except AttributeError:
			roi["Color"] = None
			roi["RGBColor"] = None
		try:
			alias = r.find("Alias").text
			roi["Alias"] = alias.split(",")
		except AttributeError:
			roi["Alias"] = None
		rois["rois"].append(roi)
	return rois


def create_prv(patient, case, examination, source_roi, df_TG263):
	"""
	:param case: RS Case Object
	:param examination: RS Examination
	:param source_roi: name of the structure to find a match to
	:param df_TG263: dataframe for the TG-263 database (loaded with iter_standard_rois)
	"""
	df_source_roi = df_TG263[df_TG263.name == source_roi]
	regex_prv = r'^'+ source_roi + r'_PRV\d{2}$'
 	df_prv = df_TG263[df_TG263.name.str.match(regex_prv) == True]
	msg = ""
	if not df_prv.empty:
		parsed_name = df_prv.name.str.extract(r'([a-zA-z_]+)([0-9]+)', re.IGNORECASE, expand=True)
		expansion_mm = int(parsed_name[1])
		expansion_cm = expansion_mm / 10.
		prv_name = df_prv.name.values[0]
		# Try to create the correct return roi or retrieve its existing geometry
		roi_geom = create_roi(case=case, examination=examination,
                              roi_name=prv_name, delete_existing=True)
  
		if roi_geom is not None:
			prv_exp_defs = {
			"StructureName": prv_name,
			"ExcludeFromExport": True,
			"VisualizeStructure": False,
			"StructColor": [ 192, 192, 192],
			"OperationA": "Union",
			"SourcesA": [source_roi],
			"MarginTypeA": "Expand",
			"ExpA": [expansion_cm] * 6,
			"OperationB": "Union",
			"SourcesB": [],
			"MarginTypeB": "Expand",
			"ExpB": [0] * 6,
			"OperationResult": "None",
			"MarginTypeR": "Expand",
			"ExpR": [0] * 6,
			"StructType": "Undefined",
		}
			make_boolean_structure(patient=patient, case=case, examination=examination, **prv_exp_defs)
			# Set color of matched structures
			if df_prv.RGBColor.values[0] is not None:
				prv_rgb = [int(x) for x in df_prv.RGBColor.values[0]]
				color_msg = change_roi_color(case=case, roi_name=prv_name, rgb=prv_rgb)
				if color_msg is None:
					msg += '{} color changed to {}'.format(prv_name,prv_rgb)
				else:
					msg += '{} could not change type. {}'.format(prv_name, color_msg)
			# Set type and OrganType of matched structures
			if df_prv.RTROIInterpretedType.values[0] is not None:
				prv_type = df_prv.RTROIInterpretedType.values[0]
				type_msg = change_roi_type(case=case, roi_name=prv_name, roi_type=prv_type)
				if type_msg is None:
					msg += '{} type changed to {}\n'.format(prv_name, prv_type)
				else:
					msg += '{} could not change type. {}\n'.format(prv_name, type_msg)
			return None
		else:
			msg += "Unable to create {}".format(prv_name)
			return msg
	else:
		msg += "Unable to find {} in the dataframe".format(source_roi)
		return msg


def match_roi(patient, case, examination, plan_rois,df_rois=None):
	"""
	Matches a input list of plan_rois (user-defined) to protocol,
	if a structure set is approved or a structure already has an existing geometry
	with the potential matched structure then this will create a copy and copy the geometry
	if the geometry is copied, then the specificity and dice coefficients are checked
	outputs data to a log
	:param patient: RS Patient Object
	:param case: RS Case Object
	:param examination: RS Examination object
	:param plan_rois:
	:return: a dictionary with matched elements
	"""
	epsilon = 1e-6  # tolerance of variation in specificity and precision (Jaccard index)
	oar_list = filter_rois(plan_rois)
	if df_rois is None:
		files = [[r"../protocols", r"", r"TG-263.xml"], [r"../protocols", r"UW", r""]]
		paths = []
		for i, f in enumerate(files):
			secondary_protocol_folder = f[0]
			institution_folder = f[1]
			paths.append(os.path.join(os.path.dirname(__file__),
						secondary_protocol_folder,
						institution_folder))
		# Generate a list of all standard names used in both protocols and TG-263
		standard_names = []
		for f in os.listdir(paths[1]):
			if f.endswith(".xml"):
				tree = xml.etree.ElementTree.parse(os.path.join(paths[1], f))
				prot_rois = tree.findall(".//roi")
				for r in prot_rois:
					if not any(i in r.find("name").text for i in standard_names):
						standard_names.append(r.find("name").text)

		tree = xml.etree.ElementTree.parse(os.path.join(paths[0], files[0][2]))
		roi263 = tree.findall("./" + "roi")
		rois_dict = iter_standard_rois(tree)
		df_rois = pd.DataFrame(rois_dict["rois"])
	# (see results using df_rois.to_string())
	# Remove the exact matches from the structure list
	del_indices = []
	for index, e in enumerate(oar_list):
	 	df_e = df_rois[df_rois.name == e]
	 	# If more than one result is returned by the dataframe search report an error
	 	if len(df_e) > 1:
	 		logging.warning('Too many matching {}. That makes me a sad panda. :('.format(e) +
                    		'It is likely the protocol file contains multiple references to the same structure')
	 	elif df_e.empty:
	 		logging.debug('{} was not found in the protocol list'.format(e))
	 	else:
	 		e_name = df_e.name.values[0]
	 		logging.debug('{} matched to  {} in protocol list'.format(e, e_name))
			del_indices.append(index)
	# Eliminate the structures with exact matches from the search.
	for indx in sorted(del_indices,reverse=True):
		del oar_list[indx]

	# Check aliases first (look in TG-263 to see if an alias is there).
	# Currently building a list of all aliases at this point (at little inefficient)
	standard_names = {}
	aliases = {}
	# Search through the dataframe for all available aliases.
 	standard_names = df_rois.set_index('name')['Alias'].to_dict()

	# Comes up with a list of up to 5 matches
	potential_matches = find_normal_structures_match(
		rois=oar_list, num_matches=5, standard_rois=standard_names
	)
	potential_matches_exacts_removed = potential_matches.copy()
	exact_match = []
	# Search the match list and if an exact match is found, pop the key
	for roi, match in potential_matches.iteritems():
		if re.match(r'^' + roi + r'$', match[0][1]):
			potential_matches_exacts_removed.pop(roi)
			exact_match.append(match[0][1])

	# Launch the dialog to get the list of matched elements
	matched_rois = match_dialog(matches=potential_matches_exacts_removed,
								elements=roi263, df_rois=df_rois)
	# Store the suffix and pop it
	suffix = matched_rois["Suffix"]
	matched_rois.pop("Suffix")
	return_rois = {}
	# matched_rois now contains:
	# the keys as the planning structures, and the elementtree element found to match (or None)
	for k, v in matched_rois.iteritems():
		# If no match was made, v will be None otherwise,
		# if there is no match in the protocols, a user-supplied
		# value can be used for the name. If it was matched then
		# it is an elementree element for roi
		if v is None:
			return_rois[k] = None
			logging.debug("Structure {k} not matched {v}".format(k=k, v=v))
		else:
			# If the value is a string, then it was manually entered by the user
			if isinstance(v, str):
				# We can only set name properties as the user has given a structure name
				# with no protocol correlate
				return_rois[k] = v
				k_user_defined = True
			# If this is pandas, then grab its name
			elif type(v) is pd.core.frame.DataFrame:
				return_rois[k] = v.name.to_string(header=False, index=False).strip()
				k_user_defined = False
			# If the value is not a string, then it is an elementtree. Retrieve its name
			else:
				return_rois[k] = v.find("name").text
				k_user_defined = False
			# Does the input structure match the protocol name entirely
			logging.debug('Post match for {k}, the value is {v}'.format(
				k=k,v=return_rois[k]
			))
			if k == return_rois[k]:
				logging.debug(
					"{} was matched to {}. No changes necessary".format(k, return_rois[k])
				)
			else:
				# Move the contents of k to return_rois[k]
				# Check if k is already approved on this examination
				k_is_approved = structure_approved(case=case, roi_name=k, examination=examination)
				# Check if there is a misnamed (case insensitive match) in this patient's case
				case_insensitive_match = case_insensitive_structure_search(
					case=case, structure_name=k
				)
				if case_insensitive_match is None:
					k_case_insensitive_match = False
				else:
					k_case_insensitive_match = True
					logging.debug('Match to {} found as {}'.format(
						k, case_insensitive_match))
				# See if the destination contour exists
				return_k_exists = check_structure_exists(case=case,
														 structure_name=return_rois[k],
														 option='Check')
				# Find all the exams which contain k
				exams_with_k = exams_containing_roi(case=case, structure_name=k)
				# If exams_with_k is empty, then no examination has contours for k
				if not exams_with_k:
					k_contours_multiple_exams = False
					k_empty = True
					k_contours_this_exam = False
				else:
					k_empty = False
					if len(exams_with_k) > 1:
						k_contours_multiple_exams = True
					else:
						k_contours_multiple_exams = False
					# Go through the list of exams which have contours for k
					# and see if any are exact matches
					for e in exams_with_k:
						k_contours_this_exam = False
						if e == examination.Name:
							# k has contours on this examination
							k_contours_this_exam = True
							break
				logging.debug('Renaming required for matching {} to {}'
							  .format(k, return_rois[k])
							  )
				# Try to just change the name of the existing contour, but if it is locked or if the
				# desired contour already exists, we'll have to replace the geometry
				# Check to see if return_rois[k] is approved or evaluate whether
				# the correct structure already exists
				if not k_contours_this_exam:
					#  there are no contours on this structure. So don't do anything with it
					logging.debug(
						"{} was matched to {}, but is empty on exam {}".format(
							k, return_rois[k], examination.Name
						)
					)
				# if k_is_approved or k_case_insensitive_match or k_contours_multiple_exams:
				if k_is_approved or k_case_insensitive_match or return_k_exists:
					logging.debug(
						"Unable to rename {} to {}, attempting a geometry copy".format(
							k, return_rois[k]
						)
					)
					# Try to create the correct return roi or retrieve its existing geometry
					roi_geom = create_roi(
						case=case,
						examination=examination,
						roi_name=return_rois[k],
						delete_existing=False,
						suffix=suffix,
					)
					if roi_geom is not None:
						# Make the geometry and validate the result
						if k_contours_this_exam:
							roi_geom.OfRoi.CreateMarginGeometry(
								Examination=examination,
								SourceRoiName=k,
								MarginSettings={
									"Type": "Expand",
									"Superior": 0.0,
									"Inferior": 0.0,
									"Anterior": 0.0,
									"Posterior": 0.0,
									"Right": 0.0,
									"Left": 0.0,
								},
							)
							# Ensure copy did not result in loss of fidelity
							geometry_validation = case.PatientModel.StructureSets[
								examination.Name
							].ComparisonOfRoiGeometries(RoiA=k, RoiB=roi_geom.OfRoi.Name)
							validation_message = []
							for metric, value in geometry_validation.iteritems():
								validation_message.append(str(metric) + ":" + str(value))
							logging.debug(
								"Roi Geometry copied from {} to {}. ".format(k, roi_geom.OfRoi.Name)
								+ "Resulting overlap metrics {}".format(validation_message)
							)
							# k exists only on this exam, so we've copied its geometry and since its
							if not k_contours_multiple_exams and k_contours_this_exam:
								if (geometry_validation["Precision"] - 1) <= epsilon and (
										geometry_validation["Sensitivity"] - 1
								) <= epsilon:
									case.PatientModel.RegionsOfInterest[k].DeleteRoi()
						else:
							if k_empty:
								case.PatientModel.RegionsOfInterest[k].DeleteRoi()
							logging.debug(
								"Roi Geometry not copied from {} to {}. ".format(
									k, roi_geom.OfRoi.Name
								)
								+ "since {} does not have contours in exam {}".format(
									k, examination.Name
								)
							)
				else:
					logging.debug("Direct rename {} to {}".format(k, return_rois[k]))
					case.PatientModel.RegionsOfInterest[k].Name = return_rois[k]
	return return_rois


def structure_approved(case, roi_name, examination=None):
	"""
	Check if structure is approved anywhere in this patient, if an exam is supplied
	only the exam supplied is checked for the approved contour
	:param case: RS case
	:param roi_name: string containing name of roi
	:param examination: RS examination object
	:return: True if structure is approved somewhere
	"""
	struct_exists = exists_roi(case=case, rois=roi_name)
	# If the structure is undefined, then is is not approved
	if not struct_exists:
		return False
	else:
		for s in case.PatientModel.StructureSets:
			if examination is not None and s.OnExamination.Name != examination.Name:
				continue
			else:
				for a in s.ApprovedStructureSets:
					try:
						for r in a.ApprovedRoiStructures:
							if r.OfRoi.Name == roi_name:
								return True
					except AttributeError:
						logging.debug("A is none {}".format(a))
						continue
		return False


def dialog_create_roi():
	"""
	Dialog to ascertain the user preference of overwrite or append on a new roi with existing geometry

	:return: overwrite or append
	"""
	dialog1 = UserInterface.InputDialog(
		inputs={
			'1': "Delete existing geometry or append a suffix",
			'2': "Suffix if needed, e.g. _R1",
		},
		title="Delete geometry or create a new structure?",
		datatype={
			'1': "combo",
			'2': "text",
		},
		initial={
			'1': "Delete Geometry",
			'2': "_R1"
		},
		options={
			'1': ["Delete Geometry",
			      "Append Suffix"
			],
			#       'Primary+Boost',
			#       'Multiple Separate Targets'],
		},
		required=['1'],
	)
	dialog1_response = dialog1.show()
	if dialog1_response == {}:
		sys.exit("Unable to proceed due to existing geometry conflict")
	# Determine user responses
	if dialog1_response['1'] == 'Delete Geometry':
		return None
	else:
		return dialog1_response['2']


def create_roi(case, examination, roi_name, delete_existing=None, suffix=None):
	"""
	Thoughtful creation of structures that can determine if the structure exists,
	determine the geometry exists on this examination
	-Create it with a suffix if the geometry exists and is locked on the current examination
	Is the structure name already in use?
		*<No>  -> Make it and return the RoiGeometry on this examination
		*<Yes> Are there contours defined for roi_name in this case?
			**<No> -> return the RoiGeometry on this examination
			**<Yes> Is the geometry approved somewhere in the case?
				***<No> Either delete it (delete_existing), or append a supplied or default suffix
				***<Yes> Is the geometry approved on this exam?
					****<No> -> Either delete it (delete_existing),
								or append a supplied or default suffix
					****<Yes> -> Return None (delete_existing),
								 or append a supplied or default suffix
	:param case:
	:param examination:
	:param roi_name: string containing name of roi to be created
	:param delete_existing: delete any existing roi with name roi_name so long as it isn't approved
	:param suffix: append the suffix string to the name of a contour
	:return: new_structure_name: the RoiGeometries object of roi_name or its suffix-modified name
	"""
	# First we want to work with the case insensitive match to the structure name supplied
	roi_name_ci = case_insensitive_structure_search(case=case, structure_name=roi_name)
	roi_name_exists = check_structure_exists(case=case,
											 option='Check',
											 structure_name=roi_name)
	# struct_exists is true if the roi_name is already defined
	if roi_name_ci is not None:
		struct_exists = True
	elif roi_name_exists:
		roi_name_ci = roi_name
		struct_exists = True
	else:
		roi_name_ci = roi_name
		struct_exists = False

	logging.debug("{} is defined somewhere in this case {}".format(roi_name_ci, struct_exists))
	# geometry_exists_in_case is True if any examination
	# in this case has contours for this roi_name_ci
	geometry_exists_in_case = check_structure_exists(
		case=case,
		structure_name=roi_name_ci,
		option="Check"
	)
	logging.debug("{} geometry exists in case: {}".format(roi_name_ci, geometry_exists_in_case))
	# geometry_exists is True if this examination has contours
	geometry_exists = check_structure_exists(
		case=case,
		structure_name=roi_name_ci,
		option="Check",
		exam=examination
	)
	logging.debug(
		"{} geometry exists in exam {}: {}".format(roi_name_ci, examination.Name, geometry_exists)
	)
	# Look through all structure sets in the patient to see if
	# roi name is approved on an exam in this patient
	geometry_approved = structure_approved(case=case, roi_name=roi_name_ci, examination=examination)
	logging.debug(
		"{} geometry approved in exam {}: {}".format(
			roi_name_ci, examination.Name, geometry_approved
		)
	)
	# If the call has been made without a suffix or deletion instructions, prompt user.
	if delete_existing is None and suffix is None:
		if geometry_exists and not geometry_approved:
     		# Prompt the user to make a decision between deleting existing geometry and a suffix
			suffix = dialog_create_roi()
			if suffix is None:
				delete_existing = True
			else:
				delete_existing = False

	if struct_exists:
		# Does the existing structure have any contours defined
		if geometry_exists_in_case:
			# Are the existing contours on this exam?
			if geometry_exists:
				# Is the existing geometry approved?
				if geometry_approved:
					# TODO if delete_existing is selected, prompt the user to unapprove or quit
					if delete_existing:
						# Delete the existing geometry and return
						# the empty geometry on the current exam
						logging.debug(
							"Exam {} has an approved geometry for {}, cannot create new roi".format(
								examination.Name, roi_name_ci
							)
						)
						return None
					else:
						# We can't delete the existing approved geometry, so we'll need to append
						i = 0
						if suffix is None:
							suffix = "_R"
						updated_roi_name = roi_name + suffix + str(i)
						while any(exists_roi(case=case, rois=updated_roi_name)):
							i += 1
							updated_roi_name = roi_name + suffix + str(i)
						# Make a new roi using the updated name
						case.PatientModel.CreateRoi(Name=updated_roi_name)
						return case.PatientModel.StructureSets[examination.Name].RoiGeometries[
							updated_roi_name
						]
				else:
					# The geometry is not approved on this examination
					if delete_existing:
						# Delete the existing geometry and return
						# the empty geometry on the current exam
						case.PatientModel.StructureSets[examination.Name].RoiGeometries[
							roi_name_ci
						].DeleteGeometry
						return case.PatientModel.StructureSets[examination.Name].RoiGeometries[
							roi_name_ci
						]
					else:
						# We don't want to delete the existing geometry, so we'll need to append
						if suffix is None:
							suffix = "_R"
						i = 1
						updated_roi_name = roi_name + suffix + str(i)
						while any(exists_roi(case=case, rois=updated_roi_name)):
							logging.debug(
								"Roi {} found in list. Checking next available.".format(
									updated_roi_name
								)
							)
							i += 1
							updated_roi_name = roi_name + suffix + str(i)
						# Make a new roi using the updated name
						case.PatientModel.CreateRoi(Name=updated_roi_name)
						return case.PatientModel.StructureSets[examination.Name].RoiGeometries[
							updated_roi_name
						]
			else:
				# Geometry exists but not on the current exam,
				# return the empty geometry on the current exam
				return case.PatientModel.StructureSets[examination.Name].RoiGeometries[roi_name_ci]
		else:
			# The existing structure is empty on all exams,
			# return the empty geometry on the current exam
			return case.PatientModel.StructureSets[examination.Name].RoiGeometries[roi_name_ci]
	else:
		# The roi does not exist, so make it and return the empty geometry for this exam
		case.PatientModel.CreateRoi(Name=roi_name_ci)
		logging.debug(
			"{} is not in the list. Creating {}".format(
				roi_name_ci,
				case.PatientModel.StructureSets[examination.Name]
					.RoiGeometries[roi_name_ci]
					.OfRoi.Name,
			)
		)
		return case.PatientModel.StructureSets[examination.Name].RoiGeometries[roi_name_ci]


def make_boolean_structure(patient, case, examination, **kwargs):
	StructureName = kwargs.get("StructureName")
	ExcludeFromExport = kwargs.get("ExcludeFromExport")
	VisualizeStructure = kwargs.get("VisualizeStructure")
	StructColor = kwargs.get("StructColor")
	SourcesA = kwargs.get("SourcesA")
	MarginTypeA = kwargs.get("MarginTypeA")
	ExpA = kwargs.get("ExpA")
	OperationA = kwargs.get("OperationA")
	SourcesB = kwargs.get("SourcesB")
	MarginTypeB = kwargs.get("MarginTypeB")
	ExpB = kwargs.get("ExpB")
	OperationB = kwargs.get("OperationB")
	MarginTypeR = kwargs.get("MarginTypeR")
	ExpR = kwargs.get("ExpR")
	OperationResult = kwargs.get("OperationResult")
	StructType = kwargs.get("StructType")
	if "VisualizationType" in kwargs:
		VisualizationType = kwargs.get("VisualizationType")
	else:
		VisualizationType = "contour"

	try:
		case.PatientModel.RegionsOfInterest[StructureName]
		logging.warning(
			"make_boolean_structure: Structure "
			+ StructureName
			+ " exists.  This will be overwritten in this examination"
		)
	except:
		create_roi(case, examination, StructureName, delete_existing=True, suffix=None)

	case.PatientModel.RegionsOfInterest[StructureName].SetAlgebraExpression(
		ExpressionA={
			"Operation": OperationA,
			"SourceRoiNames": SourcesA,
			"MarginSettings": {
				"Type": MarginTypeA,
				"Superior": ExpA[0],
				"Inferior": ExpA[1],
				"Anterior": ExpA[2],
				"Posterior": ExpA[3],
				"Right": ExpA[4],
				"Left": ExpA[5],
			},
		},
		ExpressionB={
			"Operation": OperationB,
			"SourceRoiNames": SourcesB,
			"MarginSettings": {
				"Type": MarginTypeB,
				"Superior": ExpB[0],
				"Inferior": ExpB[1],
				"Anterior": ExpB[2],
				"Posterior": ExpB[3],
				"Right": ExpB[4],
				"Left": ExpB[5],
			},
		},
		ResultOperation=OperationResult,
		ResultMarginSettings={
			"Type": MarginTypeR,
			"Superior": ExpR[0],
			"Inferior": ExpR[1],
			"Anterior": ExpR[2],
			"Posterior": ExpR[3],
			"Right": ExpR[4],
			"Left": ExpR[5],
		},
	)

	if StructureName == "InnerAir":
		logging.debug('Excluding {} from export'.format(StructureName))
	if ExcludeFromExport:
		exclude_from_export(case=case, rois=StructureName)

	msg = change_roi_color(case=case,
         		         	roi_name = StructureName,
         		         	rgb=StructColor)
	change_roi_type(case=case,roi_name=StructureName,roi_type=StructType)
	case.PatientModel.RegionsOfInterest[StructureName].UpdateDerivedGeometry(
     												   Examination=examination, Algorithm="Auto"
													   )
	patient.SetRoiVisibility(RoiName=StructureName, IsVisible=VisualizeStructure)
	patient.Set2DvisualizationForRoi(RoiName=StructureName, Mode=VisualizationType)


def make_wall(
		wall, sources, delta, patient, case, examination, inner=True, struct_type="Undefined"
):
	"""

	:param wall: Name of wall contour
	:param sources: List of source structures
	:param delta: contraction
	:param patient: current patient
	:param case: current case
	:param inner: logical create an inner wall (true) or ring
	:param examination: current exam
	:return:
	"""

	if inner:
		a = [0] * 6
		b = [delta] * 6
	else:
		a = [delta] * 6
		b = [0] * 6

	wall_defs = {
		"StructureName": wall,
		"ExcludeFromExport": True,
		"VisualizeStructure": False,
		"StructColor": [ 46, 122, 177],
		"OperationA": "Union",
		"SourcesA": sources,
		"MarginTypeA": "Expand",
		"ExpA": a,
		"OperationB": "Union",
		"SourcesB": sources,
		"MarginTypeB": "Contract",
		"ExpB": b,
		"OperationResult": "Subtraction",
		"MarginTypeR": "Expand",
		"ExpR": [0] * 6,
		"StructType": struct_type,
	}
	make_boolean_structure(patient=patient, case=case, examination=examination, **wall_defs)


def make_inner_air(PTVlist, external, patient, case, examination, inner_air_HU=-900):
	"""

	:param PTVlist: list of target structures to search near for air pockets
	:param external: string name of external to use in the definition
	:param patient: current patient
	:param case: current case
	:param examination: current examination
	:param inner_air_HU: optional parameter to define upper threshold of air volumes
	:return: new_structs: a list of newly created structures
	"""
	new_structs = []
	# Automated build of the Air contour
	air_name  = "Air"
	air_color = [ 55, 221, 159] # DarkShamrock
	air_exists = exams_containing_roi(case=case,
                                	  structure_name=air_name,
                                   	  exam=examination)
	if air_exists:
		retval_air = case.PatientModel.RegionsOfInterest[air_name]
	else:
		msg = create_roi(case=case,
                         examination=examination,
                         roi_name=air_name,
                         delete_existing=True,
                         suffix=None)
		retval_air = case.PatientModel.RegionsOfInterest[air_name]
		change_roi_color(case=case, roi_name=air_name, rgb=air_color)
		# retval_air = case.PatientModel.CreateRoi(
		# 	Name="Air",
		# 	Color="Green",
		# 	Type="Undefined",
		# 	TissueName=None,
		# 	RbeCellTypeName=None,
		# 	RoiMaterial=None,
		# )
		new_structs.append(air_name)
	patient.SetRoiVisibility(RoiName=air_name, IsVisible=False)
	exclude_from_export(case=case, rois=air_name)

	retval_air.GrayLevelThreshold(
		Examination=examination,
		LowThreshold=-1024,
		HighThreshold=inner_air_HU,
		PetUnit="",
		CbctUnit=None,
		BoundingBox=None,
	)
	inner_air_sources = [air_name, external]
	inner_air_defs = {
		"StructureName": "InnerAir",
		"ExcludeFromExport": True,
		"VisualizeStructure": False,
		"StructColor": air_color,
		"OperationA": "Union",
		"SourcesA": inner_air_sources,
		"MarginTypeA": "Expand",
		"ExpA": [0] * 6,
		"OperationB": "Union",
		"SourcesB": PTVlist,
		"MarginTypeB": "Expand",
		"ExpB": [1] * 6,
		"OperationResult": "Intersection",
		"MarginTypeR": "Expand",
		"ExpR": [0] * 6,
		"StructType": "Undefined",
	}
	make_boolean_structure(patient=patient, case=case, examination=examination, **inner_air_defs)

	# Define the inner_air structure at the Patient Model level
	inner_air_pm = case.PatientModel.RegionsOfInterest["InnerAir"]
	# Define the inner_air structure at the examination level
	inner_air_ex = case.PatientModel.StructureSets[examination.Name].RoiGeometries["InnerAir"]

	# If the InnerAir structure has contours clean them
	if inner_air_ex.HasContours():
		inner_air_pm.VolumeThreshold(
			InputRoi=inner_air_pm, Examination=examination, MinVolume=0.1, MaxVolume=500
		)
		# Check for emptied contours
		if not inner_air_ex.HasContours():
			logging.debug("Volume Thresholding has eliminated InnerAir contours")
	else:
		logging.debug("No air contours were found near the targets")

	return new_structs


def make_externalclean(
		case, examination, structure_name="ExternalClean", suffix=None, delete=False
):
	"""
	Makes a cleaned version of the external (body) contour and sets its type appropriately
	:param case: RS Case object
	:param examination: RS Examination object
	:param structure_name: a supplied external structure name
	:param suffix: optional suffix in the event of locked structures
	:param delete: deletes existing External if present
	:return: the RoiGeometries object of the cleaned external
	"""
	if delete:
		current_external = find_types(case=case, roi_type="External")
		try:
			case.RegionsOfInterest[current_external].DeleteRoi()
		except:
			logging.warning('Structure {} could not be deleted'.format(current_external))
	# Redraw the ExternalClean structure if necessary
	roi_geom = create_roi(
		case=case,
		examination=examination,
		roi_name=structure_name,
		delete_existing=False,
		suffix=suffix,
	)
	if not roi_geom.HasContours():
		roi_geom.OfRoi.CreateExternalGeometry(Examination=examination, ThresholdLevel=None)
		roi_geom.OfRoi.VolumeThreshold(
			InputRoi=roi_geom.OfRoi, Examination=examination, MinVolume=1, MaxVolume=200000
		)
	else:
		logging.warning(
			"Structure "
			+ structure_name
			+ " exists.  Using predefined structure after removing holes and changing color."
		)
	roi_geom.OfRoi.SetAsExternal()
	roi_geom.OfRoi.Color = define_sys_color([86, 68, 254])
	case.PatientModel.StructureSets[examination.Name].SimplifyContours(
		RoiNames=[structure_name],
		RemoveHoles3D=True,
		RemoveSmallContours=False,
		AreaThreshold=None,
		ReduceMaxNumberOfPointsInContours=False,
		MaxNumberOfPoints=None,
		CreateCopyOfRoi=False,
		ResolveOverlappingContours=False,
	)
	return roi_geom


class planning_structure_preferences:
	"""
	Class for getting all relevant data for creating planning structures.
	TODO: Make dialog based and xml-based
	"""

	def __init__(self):
		self.protocol_name = None
		self.origin_file = None
		self.origin_path = None
		self.number_of_targets = None
		self.first_target_number = None
		self.targets = {}
		self.use_inner_air = None
		self.use_uniform_dose = None
		self.uniform_dose_oar = {}
		self.use_under_dose = None
		self.under_dose_oar = {}
		self.plan_type = None


def dialog_number_of_targets():
	"""
	Dialog to ascertain the number of target dose levels to be used in defining
	the planning structures

	:return: planning_structures: an instance of the planning_structure_preferences class
								  with the attributes:
								  use_under_dose,
								  use_uniform_dose,
								  use_inner_air,
								  number_of_targets chosen.
	"""
	# Create an instance of the planning structure class
	planning_structures = planning_structure_preferences()

	dialog1 = UserInterface.InputDialog(
		inputs={
			'1': "Enter Number of Targets",
			'2': 'Enter the beginning target number, e.g. start numbering at 2 for PTV2, PTV3, PTV4 ...',
			'3': "Priority 1 goals present: Use Underdosing",
			'4': "Targets overlap sensitive structures: Use UniformDoses",
			'5': "Use InnerAir to avoid high-fluence due to cavities",
			'6': "Select plan type"
		},
		title="Planning Structures and Goal Selection",
		datatype={ 
            '2': "text",
			'3': "check",
			'4': "check",
			'5': "check",
		    '6': "combo"},
		initial={
			'1': "0",
			'2': "0",
			'5': ["yes"],
			'6': ["Concurrent"]
		},
		options={
			# Not yet,  Not yet.
			# '2': ['Single Target/Dose',
			#       'Concurrent',
			#       'Primary+Boost',
			#       'Multiple Separate Targets'],
			'3': ["yes"],
			'4': ["yes"],
			'5': ["yes"],
			'6': ["Concurrent",
			      "Sequential Primary+Boost(s)",
			      "Multiple Separate Targets"],
		},
		required=['1', '2', '6']
	)
	dialog1_response = dialog1.show()
	if dialog1_response == {}:
		sys.exit("Planning Structures and Goal Selection was cancelled")
	# Parse number of targets
	planning_structures.number_of_targets = int(dialog1_response['1'])
	planning_structures.first_target_number = int(dialog1_response['2'])
	if dialog1_response['6'] == "Concurrent":
		planning_structures.plan_type = "Concurrent"
	elif dialog1_response['6'] == "Sequential Primary+Boost(s)":
		planning_structures.plan_type = "Sequential"
	else:
		planning_structures.plan_type = "Multi"
	# User selected that Underdose is required
	if "yes" in dialog1_response['3']:
		planning_structures.use_under_dose = True
	else:
		planning_structures.use_under_dose = False
	# User selected that Uniformdose is required
	if "yes" in dialog1_response['4']:
		planning_structures.use_uniform_dose = True
	else:
		planning_structures.use_uniform_dose = False
	# User selected that InnerAir is required
	if "yes" in dialog1_response['5']:
		planning_structures.use_inner_air = True
	else:
		planning_structures.use_inner_air = False
	return planning_structures


def planning_structures(
		generate_ptvs=True,
		generate_ptv_evals=True,
		generate_otvs=True,
		generate_skin=True,
		generate_inner_air=True,
		generate_field_of_view=True,
		generate_ring_hd=True,
		generate_ring_ld=True,
		generate_normal_2cm=True,
		generate_combined_ptv=True,
		skin_contraction=0.3,
		run_status=True,
		planning_structure_selections=None,
		dialog2_response=None,
		dialog3_response=None,
		dialog4_response=None,
		dialog5_response=None,
):
	"""
	Generate Planning Structures

	This script is designed to help you make planning structures.
	Prior to starting you should determine:
	All structures to be treated, and their doses
	All structures with priority 1 goals
		(they are going to be selected for UnderDose)
	All structures where hot-spots are undesirable but underdosing is not desired.
		They will be placed in the UniformDose ROI.


	Raystation script to make structures used for planning.

	Note:
	Using the Standard InputDialog
	We have several calls
	The first will determine the target doses and whether we are uniform or underdosing
	Based on those responses:
	Select and Approve underdose selections
	Select and Approve uniform dose selections
	The second non-optional call prompts the user to use:
	-Target-specific rings
	-Specify desired standoffs in the rings closest to the target

	Inputs:
	None, though eventually the common uniform and underdose should be dumped into xml files
	and stored in protocols

	Usage:

	Version History:
	1.0.1: Hot fix to repair inconsistency when underdose is not used but uniform dose is.
	1.0.2: Adding "inner air" as an optional feature
	1.0.3 Hot fix to repair error in definition of sOTVu: Currently taking union of PTV and
	not_OTV - should be intersection.
	1.0.4 Bug fix for upgrade to RS 8 - replaced the toggling of the exclude from export with
	the required method.
	1.0.4b Save the user mapping for this structure set as an xml file to be loaded by create_goals
	1.0.5 Exclude InnerAir and FOV from Export, add IGRT Alignment Structure
	1.0.6 Added the Normal_1cm structure to the list


	This program is free software: you can redistribute it and/or modify it under
	the terms of the GNU General Public License as published by the Free Software
	Foundation, either version 3 of the License, or (at your option) any later version.

	This program is distributed in the hope that it will be useful, but WITHOUT
	ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
	FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

	You should have received a copy of the GNU General Public License along with
	this program. If not, see <http://www.gnu.org/licenses/>.

	:param generate_ptvs:
	:param generate_ptv_evals:
	:param generate_otvs:
	:param generate_skin:
	:param generate_inner_air:
	:param generate_field_of_view:
	:param generate_ring_hd:
	:param generate_ring_ld:
	:param generate_normal_2cm:
	:param generate_combined_ptv:
	:param skin_contraction: Contraction in cm to be used in the definition of the skin contour
	:return:
	"""
	# The following list allows different elements of the code to be toggled
	# No guarantee can be made that things will work if elements are turned off
	# all dependencies are not really resolved
	# TODO: Move this down to where the translation map gets declared
	# Xml_Out.save_structure_map()

	# InnerAir Parameters
	# Upper Bound on the air volume to be removed from target coverage considerations
	InnerAirHU = -900

	try:
		patient = connect.get_current("Patient")
		case = connect.get_current("Case")
		examination = connect.get_current("Examination")
	except:
		logging.warning("patient, case and examination must be loaded")

	if run_status:
		status = UserInterface.ScriptStatus(
			steps=[
				"User Input",
				"Support elements Generation",
				"Target Generation",
				"Ring Generation",
			],
			docstring=__doc__,
			help=__help__,
		)

	# Keep track of all rois that are created
	newly_generated_rois = []

	# If a Brain structure exists, make a Normal_1cm
	# TODO: Move this to a protocol creation
	StructureName = "Brain"
	roi_check = all(check_roi(case=case, exam=examination, rois=StructureName))
	if roi_check:
		generate_normal_1cm = True
	else:
		generate_normal_1cm = False

	# Redraw the clean external volume if necessary
	StructureName = "ExternalClean"
	roi_check = all(check_roi(case=case, exam=examination, rois=StructureName))

	if roi_check:
		retval_ExternalClean = case.PatientModel.RegionsOfInterest[StructureName]
		retval_ExternalClean.SetAsExternal()
		case.PatientModel.StructureSets[examination.Name].SimplifyContours(
			RoiNames=[StructureName],
			RemoveHoles3D=True,
			RemoveSmallContours=False,
			AreaThreshold=None,
			ReduceMaxNumberOfPointsInContours=False,
			MaxNumberOfPoints=None,
			CreateCopyOfRoi=False,
			ResolveOverlappingContours=False,
		)
		retval_ExternalClean.Color = define_sys_color([86, 68, 254])
		logging.warning(
			"Structure "
			+ StructureName
			+ " exists.  Using predefined structure after removing holes and changing color."
		)

	else:
		StructureName = "ExternalClean"
		# TODO Move to an internal create call
		retval_ExternalClean = case.PatientModel.CreateRoi(
			Name=StructureName,
			Color="86, 68, 254",
			Type="External",
			TissueName="",
			RbeCellTypeName=None,
			RoiMaterial=None,
		)
		retval_ExternalClean.CreateExternalGeometry(Examination=examination, ThresholdLevel=None)
		InExternalClean = case.PatientModel.RegionsOfInterest[StructureName]
		retval_ExternalClean.VolumeThreshold(
			InputRoi=InExternalClean, Examination=examination, MinVolume=1, MaxVolume=200000
		)
		retval_ExternalClean.SetAsExternal()
		case.PatientModel.StructureSets[examination.Name].SimplifyContours(
			RoiNames=[StructureName],
			RemoveHoles3D=True,
			RemoveSmallContours=False,
			AreaThreshold=None,
			ReduceMaxNumberOfPointsInContours=False,
			MaxNumberOfPoints=None,
			CreateCopyOfRoi=False,
			ResolveOverlappingContours=False,
		)
		newly_generated_rois.append("ExternalClean")

	if run_status:
		status.next_step(text="Please fill out the following input dialogs")
	# Commonly underdoses structures
	# Plan structures matched in this list will be selected for checkbox elements below
	# TODO: move this list to the xml file for a given protocol
	UnderStructureChoices = [
		"GreatVes",
		"A_Aorta",
		"Bag_Bowel",
		"Bowel_Small",
		"Bowel_Large",
		"BrachialPlex_L_PRV05",
		"BrachialPlex_L",
		"BrachialPlex_R",
		"BrachialPlex_R_PRV05",
		"Brainstem",
		"Bronchus",
		"Bronchus_L",
		"Bronchus_R" "CaudaEquina",
		"Cochlea_L",
		"Cochlea_R",
		"Duodenum",
		"Esophagus",
		"Genitalia",
		"Heart",
		"Eye_L",
		"Eye_R",
		"Hippocampus_L",
		"Hippocampus_L_PRV05",
		"Hippocampus_R",
		"Hippocampus_R_PRV05",
		"Lens_R",
		"Lens_L",
		"OpticChiasm",
		"OpticNerv_L",
		"OpticNerv_R",
		"Rectum",
		"SpinalCord",
		"SpinalCord_PRV02",
		"Trachea",
		"V_Pulmonary",
	]

	# Common uniformly dosed areas
	# Plan structures matched in this list will be selected for checkbox elements below
	UniformStructureChoices = [
		"A_Aorta_PRV05",
		"Bag_Bowel",
		"Bladder",
		"Bowel_Small",
		"Bowel_Large",
		"Brainstem",
		"Brainstem_PRV03",
		"Bronchus_PRV05",
		"Bronchus_L_PRV05",
		"Bronchus_R_PRV05",
		"CaudaEquina_PRV05",
		"Cochlea_L_PRV05",
		"Cochlea_R_PRV05",
		"Esophagus",
		"Esophagus_PRV05",
		"Duodenum_PRV05",
		"Heart",
		"Larynx",
		"Lens_L_PRV05",
		"Lens_R_PRV05",
		"Lips",
		"Mandible",
		"Musc_Constrict",
		"OpticChiasm_PRV03",
		"OpticNerv_L_PRV03",
		"OpticNerv_R_PRV03",
		"Rectum",
		"SpinalCord",
		"SpinalCord_PRV05",
		"Stomach",
		"Trachea",
		"V_Pulmonary_PRV05",
		"Vulva",
	]

	# Prompt the user for the number of targets, uniform dose needed, sbrt flag, underdose needed
	if planning_structure_selections is None:
		planning_structure_selections = dialog_number_of_targets()
	number_of_targets = planning_structure_selections.number_of_targets
	initial_target_offset = planning_structure_selections.first_target_number - 1
	generate_underdose = planning_structure_selections.use_under_dose
	generate_uniformdose = planning_structure_selections.use_uniform_dose
	generate_inner_air = planning_structure_selections.use_inner_air
	logging.debug(
		"Planning structures will use {} targets, UnderDose (Priority 1 Goals) {}, ".format(
			planning_structure_selections.number_of_targets,
			planning_structure_selections.use_under_dose,
		)
		+ "UniformDose {}, Inner volumes of air {}".format(
			planning_structure_selections.use_uniform_dose,
			planning_structure_selections.use_inner_air,
		)
	)

	# Determine if targets using the skin are in place

	# Find all the target names and generate the potential dropdown list for the cases
	# Use the above list for Uniform Structure Choices and Underdose choices, then
	# autoassign to the potential dropdowns
	TargetMatches = []
	UniformMatches = []
	UnderMatches = []
	AllOars = []
	for r in case.PatientModel.RegionsOfInterest:
		if r.Type == "Ptv":
			TargetMatches.append(r.Name)
		if r.Name in UniformStructureChoices:
			UniformMatches.append(r.Name)
		if r.Name in UnderStructureChoices:
			UnderMatches.append(r.Name)
		if r.OrganData.OrganType == "OrganAtRisk":
			AllOars.append(r.Name)

	translation_mapping = {}
	if dialog2_response is not None:
		input_source_list = [None] * number_of_targets
		source_doses = [None] * number_of_targets
		indx = 0
		for k, v in dialog2_response.iteritems():
			input_source_list[indx] = k
			source_doses[indx] = str(int(v))
			indx += 1

	else:
		t_i = {}
		t_o = {}
		t_d = {}
		t_r = []
		for i in range(1, number_of_targets + 1):
			j = str(i + initial_target_offset)
			k_name = j.zfill(2) + "_Aname"
			k_dose = j.zfill(2) + "_Bdose"
			t_name = "PTV" + j
			t_i[k_name] = "Match an existing plan target to " + t_name + ":"
			t_o[k_name] = TargetMatches
			t_d[k_name] = "combo"
			t_r.append(k_name)
			t_i[k_dose] = "Provide dose for plan target " + t_name + " in cGy:"
			t_r.append(k_dose)

		dialog2 = UserInterface.InputDialog(
			inputs=t_i,
			title="Input Target Dose Levels",
			datatype=t_d,
			initial={},
			options=t_o,
			required=t_r,
		)

		dialog2_response = dialog2.show()

		if dialog2_response == {}:
			sys.exit("Planning Structures and Goal Selection was cancelled")
		# Parse the output from initial_dialog
		# We are going to take a user input input_source_list and
		# convert them into PTV's used for planning
		# input_source_list consists of the user-specified targets
		# to be massaged into PTV1, PTV2, .... below

		# TODO: Replace the separate input_source_list and source_doses
		#       lists with a dictionary or a tuple
		# Process inputs
		input_source_list = [None] * number_of_targets
		source_doses = [None] * number_of_targets
		for k, v in dialog2_response.iteritems():
			# Grab the first two characters in the key and convert to an index
			i_char = k[:2]
			indx = int(i_char) - 1 - initial_target_offset
			if len(v) > 0:
				if "name" in k:
					input_source_list[indx] = v
				if "dose" in k:
					source_doses[indx] = v
			else:
				logging.warning("No dialog elements returned. Script unsuccessful")

	# Generate Scan Lengths
	if generate_combined_ptv:
		logging.debug("Creating All_PTVs ROI using Sources: {}".format(input_source_list))
		# Generate the UnderDose structure
		all_ptv_defs = {
			"StructureName": "All_PTVs",
			"ExcludeFromExport": False,
			"VisualizeStructure": False,
			"StructColor": [222, 47, 80],
			"OperationA": "Union",
			"SourcesA": input_source_list,
			"MarginTypeA": "Expand",
			"ExpA": [0] * 6,
			"OperationB": "Union",
			"SourcesB": [],
			"MarginTypeB": "Expand",
			"ExpB": [0] * 6,
			"OperationResult": "None",
			"MarginTypeR": "Expand",
			"ExpR": [0] * 6,
			"StructType": "Ptv",
		}
		make_boolean_structure(patient=patient, case=case, examination=examination, **all_ptv_defs)
		newly_generated_rois.append("All_PTVs")

	logcrit("Target List: [%s]" % ", ".join(map(str, input_source_list)))
	logcrit("Proceeding with target list: [%s]" % ", ".join(map(str, input_source_list)))
	logcrit("Proceeding with target doses: [%s]" % ", ".join(map(str, source_doses)))

	# Get a list of underdose objects from the user consisting of up to 3 inputs
	if dialog3_response is not None:
		underdose_structures = dialog3_response["structures"]
		underdose_standoff = dialog3_response["standoff"]
		logging.debug("Underdose list selected: {}".format(underdose_structures))
	else:
		# Underdose dialog call
		if generate_underdose:
			under_dose_dialog = UserInterface.InputDialog(
				title="UnderDose",
				inputs={
					"input1_underdose": "Select UnderDose Structures",
					"input2_underdose": "Select UnderDose OAR",
					"input3_underdose": "Select UnderDose OAR",
					"input4_under_standoff":
						"UnderDose Standoff: x cm gap between targets and UnderDose volume",
				},
				datatype={
					"input1_underdose": "check",
					"input2_underdose": "combo",
					"input3_underdose": "combo",
				},
				initial={"input4_under_standoff": "0.4"},
				options={
					"input1_underdose": UnderMatches,
					"input2_underdose": AllOars,
					"input3_underdose": AllOars,
				},
				required=[],
			)
			under_dose_dialog.show()
			underdose_structures = []
			try:
				underdose_structures.extend(under_dose_dialog.values["input1_underdose"])
			except KeyError:
				pass
			try:
				underdose_structures.extend([under_dose_dialog.values["input2_underdose"]])
			except KeyError:
				pass
			try:
				underdose_structures.extend([under_dose_dialog.values["input3_underdose"]])
			except KeyError:
				pass
			underdose_standoff = float(under_dose_dialog.values["input4_under_standoff"])
			logging.debug("Underdose list selected: {}".format(underdose_structures))

	# UniformDose dialog call
	if dialog4_response is not None:

		uniformdose_structures = dialog4_response["structures"]
		uniformdose_standoff = dialog4_response["standoff"]
		logging.debug("Uniform Dose list selected: {}".format(uniformdose_structures))
	else:
		if generate_uniformdose:
			uniformdose_dialog = UserInterface.InputDialog(
				title="UniformDose Selection",
				inputs={
					"input1_uniform": "Select UniformDose Structures",
					"input2_uniform": "Select UniformDose OAR",
					"input3_uniform": "Select UniformDose OAR",
					"input4_uniform_standoff":
						"UniformDose Standoff: x cm gap between targets and UniformDose volume",
				},
				datatype={
					"input1_uniform": "check",
					"input2_uniform": "combo",
					"input3_uniform": "combo",
				},
				initial={"input4_uniform_standoff": "0.4"},
				options={
					"input1_uniform": UniformMatches,
					"input2_uniform": AllOars,
					"input3_uniform": AllOars,
				},
				required=[],
			)
			uniformdose_dialog.show()
			uniformdose_structures = []
			try:
				uniformdose_structures.extend(uniformdose_dialog.values["input1_uniform"])
			except KeyError:
				pass
			try:
				uniformdose_structures.extend([uniformdose_dialog.values["input2_uniform"]])
			except KeyError:
				pass
			try:
				uniformdose_structures.extend([uniformdose_dialog.values["input3_uniform"]])
			except KeyError:
				pass
			uniformdose_standoff = float(uniformdose_dialog.values["input4_uniform_standoff"])
			logging.debug("Uniform Dose list selected: {}".format(uniformdose_structures))

	if dialog5_response is not None:
		generate_target_skin = dialog5_response["target_skin"]
		generate_ring_hd = dialog5_response["ring_hd"]
		generate_target_rings = dialog5_response["target_rings"]
		thickness_hd_ring = dialog5_response["thick_hd_ring"]
		thickness_ld_ring = dialog5_response["thick_ld_ring"]
		ring_standoff = dialog5_response["ring_standoff"]
		otv_standoff = dialog5_response["otv_standoff"]
	else:
		# OPTIONS DIALOG
		options_dialog = UserInterface.InputDialog(
			title="Options",
			inputs={
				"input1_otv_standoff": "OTV Standoff: x cm gap between higher dose targets",
				"input2_ring_standoff": "Ring Standoff: x cm gap between targets and rings",
				"input3_skintarget": "Preserve skin dose using skin-specific targets",
				"input4_targetrings": "Make target-specific High Dose (HD) rings",
				"input5_thick_hd_ring": "Thickness of the High Dose (HD) ring",
				"input6_thick_ld_ring": "Thickness of the Low Dose (LD) ring",
			},
			datatype={"input3_skintarget": "check", "input4_targetrings": "check"},
			initial={
				"input1_otv_standoff": "0.3",
				"input2_ring_standoff": "0.2",
				"input5_thick_hd_ring": "2",
				"input6_thick_ld_ring": "7",
			},
			options={
				"input3_skintarget": ["Preserve Skin Dose"],
				"input4_targetrings": ["Use target-specific rings"],
			},
			required=[],
		)

		options_response = options_dialog.show()
		if options_response == {}:
			sys.exit("Selection of planning structure options was cancelled")
		# Determine if targets using the skin are in place
		try:
			if "Preserve Skin Dose" in options_response["input3_skintarget"]:
				generate_target_skin = True
			else:
				generate_target_skin = False
		except KeyError:
			generate_target_skin = False

		# User wants target specific rings or no
		try:
			if "Use target-specific rings" in options_response["input4_targetrings"]:
				generate_target_rings = True
				generate_ring_hd = False
			else:
				generate_target_rings = False
		except KeyError:
			generate_target_rings = False

		logging.debug("User Selected Preserve Skin Dose: {}".format(generate_target_skin))

		logging.debug("User Selected target Rings: {}".format(generate_target_rings))

		# DATA PARSING FOR THE OPTIONS MENU
		# Stand - Off Values - Gaps between structures
		# cm gap between higher dose targets (used for OTV volumes)
		otv_standoff = float(options_response["input1_otv_standoff"])

		# ring_standoff: cm Expansion between targets and rings
		ring_standoff = float(options_response["input2_ring_standoff"])

		# Ring thicknesses
		thickness_hd_ring = float(options_response["input5_thick_hd_ring"])
		thickness_ld_ring = float(options_response["input6_thick_ld_ring"])

	if run_status:
		status.next_step(
			text="Support structures used for removing air, skin, and overlap being generated"
		)

	if generate_ptvs:
		# Build the name list for the targets
		PTVPrefix = "PTV"
		OTVPrefix = "OTV"
		sotvu_prefix = "sOTVu"
		# Generate a list of names for the PTV's, Evals, OTV's and EZ (exclusion zones)
		PTVList = []
		PTVEvalList = []
		OTVList = []
		PTVEZList = []
		sotvu_list = []
		high_med_low_targets = False
		numbered_targets = True
		for index, target in enumerate(input_source_list):
			if high_med_low_targets:
				NumMids = len(input_source_list) - 2
				if index == 0:
					PTVName = PTVPrefix + "_High"
					PTVEvalName = PTVPrefix + "_Eval_High"
					PTVEZName = PTVPrefix + "_EZ_High"
					OTVName = OTVPrefix + "_High"
					sotvu_name = sotvu_prefix + "_High"
				elif index == len(input_source_list) - 1:
					PTVName = PTVPrefix + "_Low"
					PTVEvalName = PTVPrefix + "_Eval_Low"
					PTVEZName = PTVPrefix + "_EZ_Low"
					OTVName = OTVPrefix + "_Low"
					sotvu_name = sotvu_prefix + "_Low"
				else:
					MidTargetNumber = index - 1
					PTVName = PTVPrefix + "_Mid" + str(MidTargetNumber)
					PTVEvalName = PTVPrefix + "_Eval_Mid" + str(MidTargetNumber)
					PTVEZName = PTVPrefix + "_EZ_Mid" + str(MidTargetNumber)
					OTVName = OTVPrefix + "_Mid" + str(MidTargetNumber)
					sotvu_name = sotvu_prefix + "_Mid" + str(MidTargetNumber)
			elif numbered_targets:
				PTVName = PTVPrefix + str(index + initial_target_offset + 1) + "_" + source_doses[index]
				PTVEvalName = PTVPrefix + str(index + initial_target_offset + 1) + "_Eval_" + source_doses[index]
				PTVEZName = PTVPrefix + str(index + initial_target_offset + 1) + "_EZ_" + source_doses[index]
				OTVName = OTVPrefix + str(index + initial_target_offset + 1) + "_" + source_doses[index]
				sotvu_name = sotvu_prefix + str(index + initial_target_offset + 1) + "_" + source_doses[index]
			PTVList.append(PTVName)
			translation_mapping[PTVName] = [input_source_list[index], str(source_doses[index])]
			PTVEvalList.append(PTVEvalName)
			PTVEZList.append(PTVEZName)
			translation_mapping[OTVName] = [input_source_list[index], str(source_doses[index])]
			OTVList.append(OTVName)
			sotvu_list.append(sotvu_name)
	else:
		logging.warning("Generate PTV's off - a nonsupported operation")

	TargetColors = [
				    [227,26,28], # BrewerRed
					[51,160,44], # BrewerDarkGreen
					[31,120,180], # BrewerDarkBlue
					[255,127,0], # BrewerOrange
					[106,61,154], # BrewerPurple
					[177,89,40], # BrewerBrown
					[255,255,51], # BrewerEsqueYellow
	]
	derived_target_colors = [
					[251,154,153], # BrewerRose
					[178,223,138], # BrewerLightGreen
					[166,206,227], # BrewerLightBlue
					[253,191,111], # BrewerLightOrange
					[202,178,214], # BrewerLightPurple
					[227,164,130], # BreweresqueLightBrown
					[255,255,153], # BrewerLightYellow
	]
	derived_ring_colors = [
					[159,96,97], # BrewerUnsatRed
					[80,128,77], # BrewerUnsatGreen
					[78,110,131], # BrewerUnsatBlue
					[159,128,96], # BrewerUnsatOrange
					[106,80,134], # BrewerUnsatPurple	
					[137,101,82], # BrewerUnsatBrown
					[179,179,128], # BrewerUnsatYellow
	]



	for k, v in translation_mapping.iteritems():
		logging.debug("The translation map k is {} and v {}".format(k, v))

	if generate_skin:
		make_wall(
			wall="Skin_PRV03",
			sources=["ExternalClean"],
			delta=skin_contraction,
			patient=patient,
			case=case,
			examination=examination,
			inner=True,
			struct_type="Organ",
		)
		newly_generated_rois.append("Skin_PRV03")

	# Generate the UnderDose structure and the UnderDose_Exp structure
	if generate_underdose:
		logging.debug("Creating UnderDose ROI using Sources: {}".format(underdose_structures))
		# Generate the UnderDose structure
		underdose_defs = {
			"StructureName": "UnderDose",
			"ExcludeFromExport": True,
			"VisualizeStructure": False,
			"StructColor": [67, 65, 225],
			"OperationA": "Union",
			"SourcesA": underdose_structures,
			"MarginTypeA": "Expand",
			"ExpA": [0] * 6,
			"OperationB": "Union",
			"SourcesB": [],
			"MarginTypeB": "Expand",
			"ExpB": [0] * 6,
			"OperationResult": "None",
			"MarginTypeR": "Expand",
			"ExpR": [0] * 6,
			"StructType": "Undefined",
		}
		make_boolean_structure(
			patient=patient, case=case, examination=examination, **underdose_defs
		)
		newly_generated_rois.append("UnderDose")
		UnderDoseExp_defs = {
			"StructureName": "UnderDose_Exp",
			"ExcludeFromExport": True,
			"VisualizeStructure": False,
			"StructColor": [ 192, 192, 192],
			"OperationA": "Union",
			"SourcesA": underdose_structures,
			"MarginTypeA": "Expand",
			"ExpA": [underdose_standoff] * 6,
			"OperationB": "Union",
			"SourcesB": [],
			"MarginTypeB": "Expand",
			"ExpB": [0] * 6,
			"OperationResult": "None",
			"MarginTypeR": "Expand",
			"ExpR": [0] * 6,
			"StructType": "Undefined",
		}
		make_boolean_structure(
			patient=patient, case=case, examination=examination, **UnderDoseExp_defs
		)
		newly_generated_rois.append("UnderDose_Exp")

	# Generate the UniformDose structure
	if generate_uniformdose:
		logging.debug("Creating UniformDose ROI using Sources: {}".format(uniformdose_structures))
		if generate_underdose:
			logging.debug("UnderDose structures required, excluding overlap from UniformDose")
			uniformdose_defs = {
				"StructureName": "UniformDose",
				"ExcludeFromExport": True,
				"VisualizeStructure": False,
				"StructColor": [ 46, 122, 177],
				"OperationA": "Union",
				"SourcesA": uniformdose_structures,
				"MarginTypeA": "Expand",
				"ExpA": [0] * 6,
				"OperationB": "Union",
				"SourcesB": underdose_structures,
				"MarginTypeB": "Expand",
				"ExpB": [0] * 6,
				"OperationResult": "Subtraction",
				"MarginTypeR": "Expand",
				"ExpR": [0] * 6,
				"StructType": "Undefined",
			}
		else:
			uniformdose_defs = {
				"StructureName": "UniformDose",
				"ExcludeFromExport": True,
				"VisualizeStructure": False,
				"StructColor": [ 46, 122, 177],
				"OperationA": "Union",
				"SourcesA": uniformdose_structures,
				"MarginTypeA": "Expand",
				"ExpA": [0] * 6,
				"OperationB": "Union",
				"SourcesB": [],
				"MarginTypeB": "Expand",
				"ExpB": [0] * 6,
				"OperationResult": "None",
				"MarginTypeR": "Expand",
				"ExpR": [0] * 6,
				"StructType": "Undefined",
			}
		make_boolean_structure(
			patient=patient, case=case, examination=examination, **uniformdose_defs
		)
		newly_generated_rois.append("UniformDose")

	if run_status:
		status.next_step(text="Targets being generated")
	# Make the primary targets, PTV1... these are limited by external and overlapping targets
	if generate_ptvs:
		# Limit each target to the ExternalClean surface
		ptv_sources = ["ExternalClean"]
		# Initially, there are no targets to use in the subtraction
		subtract_targets = []
		for i, t in enumerate(input_source_list):
			logging.debug("Creating target {} using {}".format(PTVList[i], t))
			ptv_sources.append(t)
			if i == 0:
				ptv_definitions = {
					"StructureName": PTVList[i],
					"ExcludeFromExport": True,
					"VisualizeStructure": False,
					"VisualizationType": "Filled",
					"StructColor": TargetColors[i],
					"OperationA": "Union",
					"SourcesA": [t],
					"MarginTypeA": "Expand",
					"ExpA": [0] * 6,
					"OperationB": "Union",
					"SourcesB": [],
					"MarginTypeB": "Expand",
					"ExpB": [0] * 6,
					"OperationResult": "None",
					"MarginTypeR": "Expand",
					"ExpR": [0] * 6,
					"StructType": "Ptv",
				}
			else:
				ptv_definitions = {
					"StructureName": PTVList[i],
					"ExcludeFromExport": True,
					"VisualizeStructure": False,
					"VisualizationType": "Filled",
					"StructColor": TargetColors[i],
					"OperationA": "Union",
					"SourcesA": [t],
					"MarginTypeA": "Expand",
					"ExpA": [0] * 6,
					"OperationB": "Union",
					"SourcesB": subtract_targets,
					"MarginTypeB": "Expand",
					"ExpB": [0] * 6,
					"OperationResult": "Subtraction",
					"MarginTypeR": "Expand",
					"ExpR": [0] * 6,
					"StructType": "Ptv",
				}
			logging.debug("Creating main target {}: {}".format(i, PTVList[i]))
			make_boolean_structure(
				patient=patient, case=case, examination=examination, **ptv_definitions
			)
			newly_generated_rois.append(ptv_definitions.get("StructureName"))
			subtract_targets.append(PTVList[i])

	# Make the InnerAir structure
	if generate_inner_air:
		air_list = make_inner_air(
			PTVlist=PTVList,
			external="ExternalClean",
			patient=patient,
			case=case,
			examination=examination,
			inner_air_HU=InnerAirHU,
		)
		newly_generated_rois.append(air_list)
		logging.debug("Built Air and InnerAir structures.")
	else:
		try:
			# If InnerAir is found, it's geometry should be blanked out.
			StructureName = "InnerAir"
			retval_innerair = case.PatientModel.RegionsOfInterest[StructureName]
			logging.warning("Structure " + StructureName + " exists. Geometry will be redefined")
			case.PatientModel.StructureSets[examination.Name].RoiGeometries[
				"InnerAir"
			].DeleteGeometry()
			# TODO Move to an internal create call
			case.PatientModel.CreateRoi(
				Name="InnerAir",
				Color="SaddleBrown",
				Type="Undefined",
				TissueName=None,
				RbeCellTypeName=None,
				RoiMaterial=None,
			)
		except:
			# TODO Move to an internal create call
			case.PatientModel.CreateRoi(
				Name="InnerAir",
				Color="SaddleBrown",
				Type="Undefined",
				TissueName=None,
				RbeCellTypeName=None,
				RoiMaterial=None,
			)

	# Generate a rough field of view contour.
	# It should really be put in with the dependent structures
	if generate_field_of_view:
		# Automated build of the Air contour
		fov_name = "FieldOfView"
		try:
			patient.SetRoiVisibility(RoiName=fov_name, IsVisible=False)
		except:
			# TODO Move to an internal create call
			case.PatientModel.CreateRoi(
				Name=fov_name,
				Color="192, 192, 192",
				Type="FieldOfView",
				TissueName=None,
				RbeCellTypeName=None,
				RoiMaterial=None,
			)
			case.PatientModel.RegionsOfInterest[fov_name].CreateFieldOfViewROI(
				ExaminationName=examination.Name
			)
			case.PatientModel.StructureSets[examination.Name].SimplifyContours(
				RoiNames=[fov_name], MaxNumberOfPoints=20, ReduceMaxNumberOfPointsInContours=True
			)
			patient.SetRoiVisibility(RoiName=fov_name, IsVisible=False)
			exclude_from_export(case=case, rois=fov_name)
			newly_generated_rois.append(fov_name)

	# Make the PTVEZ objects now
	if generate_underdose:
		# Loop over the PTV_EZs
		for index, target in enumerate(PTVList):
			ptv_ez_name = "PTV" + str(index + 1) + "_EZ"
			logging.debug(
				"Creating exclusion zone target {}: {}".format(str(index + 1), ptv_ez_name)
			)
			# Generate the PTV_EZ
			PTVEZ_defs = {
				"StructureName": PTVEZList[index],
				"ExcludeFromExport": True,
				"VisualizeStructure": False,
				"StructColor": derived_target_colors[index],
				"OperationA": "Union",
				"SourcesA": [target],
				"MarginTypeA": "Expand",
				"ExpA": [0] * 6,
				"OperationB": "Union",
				"SourcesB": ["UnderDose"],
				"MarginTypeB": "Expand",
				"ExpB": [0] * 6,
				"OperationResult": "Intersection",
				"MarginTypeR": "Expand",
				"ExpR": [0] * 6,
				"StructType": "Ptv",
			}
			make_boolean_structure(
				patient=patient, case=case, examination=examination, **PTVEZ_defs
			)
			newly_generated_rois.append(PTVEZ_defs.get("StructureName"))

	# We will subtract the adjoining air, skin, or Priority 1 ROI that overlaps the target
	if generate_ptv_evals:
		if generate_underdose:
			eval_subtract = ["Skin_PRV03", "InnerAir", "UnderDose"]
			logging.debug("Removing the following from eval structures".format(eval_subtract))
			if not any(exists_roi(case=case, rois=eval_subtract)):
				logging.error(
					"Missing structure needed for UnderDose: {} needed".format(eval_subtract)
				)
				sys.exit("Missing structure needed for UnderDose: {} needed".format(eval_subtract))

		else:
			eval_subtract = ["Skin_PRV03", "InnerAir"]
			logging.debug("Removing the following from eval structures".format(eval_subtract))
			if not any(exists_roi(case=case, rois=eval_subtract)):
				logging.error(
					"Missing structure needed for UnderDose: {} needed".format(eval_subtract)
				)
				sys.exit("Missing structure needed for UnderDose: {} needed".format(eval_subtract))

		for index, target in enumerate(PTVList):
			logging.debug(
				"Creating evaluation target {}: {}".format(str(index + 1), PTVEvalList[index])
			)
			# Set the Sources Structure for Evals
			PTVEval_defs = {
				"StructureName": PTVEvalList[index],
				"ExcludeFromExport": True,
				"VisualizeStructure": False,
				"StructColor": TargetColors[index],
				"OperationA": "Intersection",
				"SourcesA": [target, "ExternalClean"],
				"MarginTypeA": "Expand",
				"ExpA": [0] * 6,
				"OperationB": "Union",
				"SourcesB": eval_subtract,
				"MarginTypeB": "Expand",
				"ExpB": [0] * 6,
				"OperationResult": "Subtraction",
				"MarginTypeR": "Expand",
				"ExpR": [0] * 6,
				"StructType": "Ptv",
			}
			make_boolean_structure(
				patient=patient, case=case, examination=examination, **PTVEval_defs
			)
			newly_generated_rois.append(PTVEval_defs.get("StructureName"))
			# Append the current target to the list of targets to subtract in the next iteration
			eval_subtract.append(target)

	# Generate the OTV's
	# Build a region called z_derived_not_exp_underdose that
	# does not include the underdose expansion
	if generate_otvs:
		otv_intersect = []
		if generate_underdose:
			otv_subtract = ["Skin_PRV03", "InnerAir", "UnderDose_Exp"]
		else:
			otv_subtract = ["Skin_PRV03", "InnerAir"]
		logging.debug("otvs will not include {}".format(otv_subtract))

		not_otv_definitions = {
			"StructureName": "z_derived_not_otv",
			"ExcludeFromExport": True,
			"VisualizeStructure": False,
			"StructColor": [192, 192, 192],
			"OperationA": "Union",
			"SourcesA": ["ExternalClean"],
			"MarginTypeA": "Expand",
			"ExpA": [0] * 6,
			"OperationB": "Union",
			"SourcesB": otv_subtract,
			"MarginTypeB": "Expand",
			"ExpB": [0] * 6,
			"OperationResult": "Subtraction",
			"MarginTypeR": "Expand",
			"ExpR": [0] * 6,
			"StructType": "Undefined",
		}
		make_boolean_structure(
			patient=patient, case=case, examination=examination, **not_otv_definitions
		)
		newly_generated_rois.append(not_otv_definitions.get("StructureName"))
		otv_intersect.append(not_otv_definitions.get("StructureName"))

		# otv_subtract will store the expanded higher dose targets
		otv_subtract = []
		for index, target in enumerate(PTVList):
			OTV_defs = {
				"StructureName": OTVList[index],
				"ExcludeFromExport": True,
				"VisualizeStructure": False,
				"StructColor": derived_target_colors[index],
				"OperationA": "Intersection",
				"SourcesA": [target] + otv_intersect,
				"MarginTypeA": "Expand",
				"ExpA": [0] * 6,
				"OperationB": "Union",
				"MarginTypeB": "Expand",
				"MarginTypeR": "Expand",
				"ExpR": [0] * 6,
				"StructType": "Ptv",
			}
			if index == 0:
				OTV_defs["SourcesB"] = []
				OTV_defs["OperationResult"] = "None"
				OTV_defs["ExpB"] = [0] * 6
			else:
				OTV_defs["SourcesB"] = otv_subtract
				OTV_defs["OperationResult"] = "Subtraction"
				OTV_defs["ExpB"] = [otv_standoff] * 6

			make_boolean_structure(patient=patient, case=case, examination=examination, **OTV_defs)
			otv_subtract.append(PTVList[index])
			newly_generated_rois.append(OTV_defs.get("StructureName"))

			# make the sOTVu structures now
		if generate_uniformdose:
			# Loop over the sOTVu's
			for index, target in enumerate(PTVList):
				logging.debug(
					"Creating uniform zone target {}: {}".format(str(index + 1), sotvu_name)
				)
				# Generate the sOTVu
				sotvu_defs = {
					"StructureName": sotvu_list[index],
					"ExcludeFromExport": True,
					"VisualizeStructure": False,
					"StructColor": derived_target_colors[index],
					"OperationA": "Intersection",
					"SourcesA": [target] + otv_intersect,
					"MarginTypeA": "Expand",
					"ExpA": [0] * 6,
					"OperationB": "Union",
					"SourcesB": ["UniformDose"],
					"MarginTypeB": "Expand",
					"ExpB": [uniformdose_standoff] * 6,
					"OperationResult": "Intersection",
					"MarginTypeR": "Expand",
					"ExpR": [0] * 6,
					"StructType": "Ptv",
				}
				make_boolean_structure(
					patient=patient, case=case, examination=examination, **sotvu_defs
				)
				newly_generated_rois.append(sotvu_defs.get("StructureName"))

	# Target creation complete moving on to rings
	if run_status:
		status.next_step(text="Rings being generated")

	# RINGS

	# First make an ExternalClean-limited expansion volume
	# This will be the outer boundary for any expansion: a

	z_derived_exp_ext_defs = {
		"StructureName": "z_derived_exp_ext",
		"ExcludeFromExport": True,
		"VisualizeStructure": False,
		"StructColor": [ 192, 192, 192],
		"SourcesA": [fov_name],
		"MarginTypeA": "Expand",
		"ExpA": [8] * 6,
		"OperationA": "Union",
		"SourcesB": ["ExternalClean"],
		"MarginTypeB": "Expand",
		"ExpB": [0] * 6,
		"OperationB": "Union",
		"MarginTypeR": "Expand",
		"ExpR": [0] * 6,
		"OperationResult": "Subtraction",
		"StructType": "Undefined",
	}
	make_boolean_structure(
		patient=patient, case=case, examination=examination, **z_derived_exp_ext_defs
	)
	newly_generated_rois.append(z_derived_exp_ext_defs.get("StructureName"))

	# This structure will be all targets plus the standoff: b
	z_derived_targets_plus_standoff_ring_defs = {
		"StructureName": "z_derived_targets_plus_standoff_ring_defs",
		"ExcludeFromExport": True,
		"VisualizeStructure": False,
		"StructColor": [ 192, 192, 192],
		"SourcesA": PTVList,
		"MarginTypeA": "Expand",
		"ExpA": [ring_standoff] * 6,
		"OperationA": "Union",
		"SourcesB": [],
		"MarginTypeB": "Expand",
		"ExpB": [0] * 6,
		"OperationB": "Union",
		"MarginTypeR": "Expand",
		"ExpR": [0] * 6,
		"OperationResult": "None",
		"StructType": "Undefined",
	}
	make_boolean_structure(
		patient=patient,
		case=case,
		examination=examination,
		**z_derived_targets_plus_standoff_ring_defs
	)
	newly_generated_rois.append(z_derived_targets_plus_standoff_ring_defs.get("StructureName"))
	# Now generate a ring for each target
	# Each iteration will add the higher dose targets and
	# rings to the subtract list for subsequent rings
	# ring(i) = [PTV(i) + thickness] - [a + b + PTV(i-1)]
	# where ring_avoid_subtract = [a + b + PTV(i-1)]
	ring_avoid_subtract = [
		z_derived_exp_ext_defs.get("StructureName"),
		z_derived_targets_plus_standoff_ring_defs.get("StructureName"),
	]

	if generate_target_rings:
		logging.debug("Target specific rings being constructed")
		for index, target in enumerate(PTVList):
			ring_name = "ring" + str(index + initial_target_offset + 1) + "_" + source_doses[index]
			target_ring_defs = {
				"StructureName": ring_name,
				"ExcludeFromExport": True,
				"VisualizeStructure": False,
				"StructColor": derived_ring_colors[index],
				"OperationA": "Union",
				"SourcesA": [target],
				"MarginTypeA": "Expand",
				"ExpA": [thickness_hd_ring + ring_standoff] * 6,
				"OperationB": "Union",
				"SourcesB": ring_avoid_subtract,
				"MarginTypeB": "Expand",
				"ExpB": [0] * 6,
				"OperationResult": "Subtraction",
				"MarginTypeR": "Expand",
				"ExpR": [0] * 6,
				"StructType": "Avoidance",
			}
			make_boolean_structure(
				patient=patient, case=case, examination=examination, **target_ring_defs
			)
			newly_generated_rois.append(target_ring_defs.get("StructureName"))
			# Append the current target to the list of targets to subtract in the next iteration
			ring_avoid_subtract.append(target_ring_defs.get("StructureName"))

	else:
		# Ring_HD
		if generate_ring_hd:
			ring_hd_defs = {
				"StructureName": "Ring_HD",
				"ExcludeFromExport": True,
				"VisualizeStructure": False,
				"StructColor": [252, 179, 231],
				"SourcesA": PTVList,
				"MarginTypeA": "Expand",
				"ExpA": [ring_standoff + thickness_hd_ring] * 6,
				"OperationA": "Union",
				"SourcesB": ring_avoid_subtract,
				"MarginTypeB": "Expand",
				"ExpB": [0] * 6,
				"OperationB": "Union",
				"MarginTypeR": "Expand",
				"ExpR": [0] * 6,
				"OperationResult": "Subtraction",
				"StructType": "Avoidance",
			}
			make_boolean_structure(
				patient=patient, case=case, examination=examination, **ring_hd_defs
			)
			newly_generated_rois.append(ring_hd_defs.get("StructureName"))
			# Append RingHD to the structure list for removal from Ring_LD
			ring_avoid_subtract.append(ring_hd_defs.get("StructureName"))
	# Ring_LD
	if generate_ring_ld:
		ring_ld_defs = {
			"StructureName": "Ring_LD",
			"ExcludeFromExport": True,
			"VisualizeStructure": False,
			"StructColor": [232, 201, 223],
			"SourcesA": PTVList,
			"MarginTypeA": "Expand",
			"ExpA": [ring_standoff + thickness_hd_ring + thickness_ld_ring] * 6,
			"OperationA": "Union",
			"SourcesB": ring_avoid_subtract,
			"MarginTypeB": "Expand",
			"ExpB": [0] * 6,
			"OperationB": "Union",
			"MarginTypeR": "Expand",
			"ExpR": [0] * 6,
			"OperationResult": "Subtraction",
			"StructType": "Avoidance",
		}
		make_boolean_structure(patient=patient, case=case, examination=examination, **ring_ld_defs)
		newly_generated_rois.append(ring_ld_defs.get("StructureName"))

	# Normal_2cm
	if generate_normal_2cm:
		Normal_2cm_defs = {
			"StructureName": "Normal_2cm",
			"ExcludeFromExport": True,
			"VisualizeStructure": False,
			"StructColor": [183, 87, 145],
			"SourcesA": ["ExternalClean"],
			"MarginTypeA": "Expand",
			"ExpA": [0] * 6,
			"OperationA": "Union",
			"SourcesB": PTVList,
			"MarginTypeB": "Expand",
			"ExpB": [2] * 6,
			"OperationB": "Union",
			"MarginTypeR": "Expand",
			"ExpR": [0] * 6,
			"OperationResult": "Subtraction",
			"StructType": "Avoidance",
		}
		make_boolean_structure(
			patient=patient, case=case, examination=examination, **Normal_2cm_defs
		)
		newly_generated_rois.append(Normal_2cm_defs.get("StructureName"))

	if generate_normal_1cm:
		Normal_1cm_defs = {
			"StructureName": "Normal_1cm",
			"ExcludeFromExport": True,
			"VisualizeStructure": False,
			"StructColor": [183, 87, 145],
			"SourcesA": ["ExternalClean"],
			"MarginTypeA": "Expand",
			"ExpA": [0] * 6,
			"OperationA": "Union",
			"SourcesB": PTVList,
			"MarginTypeB": "Expand",
			"ExpB": [1] * 6,
			"OperationB": "Union",
			"MarginTypeR": "Expand",
			"ExpR": [0] * 6,
			"OperationResult": "Subtraction",
			"StructType": "Avoidance",
		}
		make_boolean_structure(
			patient=patient, case=case, examination=examination, **Normal_1cm_defs
		)
		newly_generated_rois.append(Normal_1cm_defs.get("StructureName"))

	if run_status:
		status.finish(text="The script executed successfully")
