#!/usr/bin/env python

import plistlib
import argparse
import logging

kCCBSizeTypeAbsolute = 0
kCCBSizeTypePercent = 1
kCCBSizeTypeRelativeContainer = 2
kCCBSizeTypeHorizontalPercent = 3
kCCBSizeTypeVerticalPercent = 4
kCCBSizeTypeMultiplyResolution = 5

def absolutePosition(node, parentSize):
	positionProp = None
	for prop in node['properties']:
		if prop['type'] == 'Position':
			positionProp = prop
			break

	if positionProp is None:
		return [0, 0]

	pt = positionProp['value']
	posType = pt[2]

	absPt = [0, 0]

	if posType == kCCBPositionTypeRelativeBottomLeft or posType == kCCBPositionTypeMultiplyResolution:
		absPt = pt
	elif posType == kCCBPositionTypeRelativeTopLeft:
		absPt[0] = pt[0]
		absPt[1] = parentSize[1] - pt[1]
	elif posType == kCCBPositionTypeRelativeTopRight:
		absPt[0] = parentSize[0] - pt[0]
		absPt[1] = parentSize[1] - pt[1]
	elif posType == kCCBPositionTypeRelativeBottomRight:
		absPt[0] = parentSize[0] - pt[0]
		absPt[1] = pt[1]
	elif posType == kCCBPositionTypePercent:
		absPt[0] = int(parentSize[0] * pt[0] / 100.0)
		absPt[1] = int(parentSize[1] * pt[1] / 100.0)
	
	return absPt

def offsetAbsolutePosition(positionProp, parentSize, offset):
	posType = positionProp['value'][2]

	pos = [positionProp['value'][0] + offset[0], positionProp['value'][1] + offset[1]]

	finalPos = [0, 0]

	if posType == kCCBPositionTypeRelativeBottomLeft or posType == kCCBPositionTypeMultiplyResolution:
		finalPos = pos
	elif posType == kCCBPositionTypeRelativeTopLeft:
		finalPos[0] = pos[0]
		finalPos[1] = parentSize[1] - pos[1]
	elif posType == kCCBPositionTypeRelativeTopRight:
		finalPos[0] = parentSize[0] - pos[0]
		finalPos[1] = parentSize[1] - pos[1]
	elif posType == kCCBPositionTypeRelativeBottomRight:
		finalPos[0] = parentSize[0] - pos[0]
		finalPos[1] = pos[1]
	elif posType == kCCBPositionTypePercent:
		if parentSize[0] == 0:
			finalPos[0] = pos[0]
		else:
			finalPos[0] = pos[0] * 100.0 / parentSize[0]
		if parentSize[1] == 0:
			finalPos[1] = pos[1]
		else:
			finalPos[1] = pos[1] * 100.0 / parentSize[1]

	positionProp['value'][0] = finalPos[0]
	positionProp['value'][1] = finalPos[1]

def stripCCLayer(node):
	isColorLayer = node['baseClass'] == 'CCLayerColor'
	isGradientLayer = node['baseClass'] == 'CCLayerGradient'
	if node['baseClass'] == 'CCLayer' or isColorLayer or isGradientLayer:
		if isColorLayer:
			node['baseClass'] = 'CCNodeColor'
		elif isGradientLayer:
			node['baseClass'] = 'CCNodeGradient'
		else:
			node['baseClass'] = 'CCNode'
		
		# Strip invalid properties
		stripProps = ['touchEnabled', 'mouseEnabled']
		props = node['properties']
		for prop in list(props):
			if prop['name'] in stripProps:
				props.remove(prop)

def convertOpacity(node):
	for prop in node['properties']:
		if prop['name'] == 'opacity':
			prop['type'] = 'Float'
			prop['value'] /= 255.0

			value = prop.get('baseValue')
			if value is not None:
				prop['baseValue'] = value / 255.0
	
	if 'animatedProperties' in node:
		for index, prop in node['animatedProperties'].iteritems():
			if 'opacity' in prop:
				prop['opacity']['type'] = 10
				for keyframe in prop['opacity']['keyframes']:
					keyframe['value'] /= 255.0
					keyframe['type'] = 10

def convertParticleSystem(node):
	if node['baseClass'] == 'CCParticleSystemQuad':
		node['baseClass'] = 'CCParticleSystem'

def convertAndStripIgnoreAnchorPointForPosition(parent, parentSize, absSize, node):
	props = node['properties']
	convert = False
	anchorProperty = None
	positionProperty = None
	for prop in list(props):
		if prop['type'] == 'Position':
			positionProperty = prop
		if prop['name'] == 'ignoreAnchorPointForPosition':
			props.remove(prop)
			convert = convert or prop['value']
		if prop['name'] == 'anchorPoint':
			anchorProperty = prop
	
	if parent is None:
		anchorProperty['value'] = [0, 0]
	
	if positionProperty is None and 'animatedProperties' in node:
		# No position property. That means it's animated. Oh no.
		for index, prop in node['animatedProperties'].iteritems():
			if 'position' in prop:
				positionProperty = prop['position']
				break
	
	if positionProperty is not None and convert:
		offset = [anchorProperty['value'][0] * absSize[0], anchorProperty['value'][1] * absSize[1]]
		if 'keyframes' in positionProperty:
			for keyframe in positionProperty['keyframes']:
				offsetAbsolutePosition(keyframe, parentSize, offset)
		else:
			offsetAbsolutePosition(positionProperty, parentSize, offset)

CCPositionUnitPoints = 0
CCPositionUnitUIPoints = 1
CCPositionUnitNormalized = 2

CCPositionReferenceCornerBottomLeft = 0
CCPositionReferenceCornerTopLeft = 1
CCPositionReferenceCornerTopRight = 2
CCPositionReferenceCornerBottomRight = 3

kCCBPositionTypeRelativeBottomLeft = 0
kCCBPositionTypeRelativeTopLeft = 1
kCCBPositionTypeRelativeTopRight = 2
kCCBPositionTypeRelativeBottomRight = 3
kCCBPositionTypePercent = 4
kCCBPositionTypeMultiplyResolution = 5

def convertPosition(node):
	posType = -1
	for prop in node['properties']:
		if prop['type'] == 'Position':
			value = prop['value']
			if len(value) < 5:
				posType = value[2]

				while len(value) < 5:
					value.append(0)

				if posType == kCCBPositionTypeRelativeBottomLeft:
					value[2] = CCPositionReferenceCornerBottomLeft
					value[3] = value[4] = CCPositionUnitPoints
				elif posType == kCCBPositionTypeMultiplyResolution:
					value[2] = CCPositionReferenceCornerBottomLeft
					value[3] = value[4] = CCPositionUnitUIPoints
				elif posType == kCCBPositionTypeRelativeTopLeft:
					value[2] = CCPositionReferenceCornerTopLeft
					value[3] = value[4] = CCPositionUnitPoints
				elif posType == kCCBPositionTypeRelativeTopRight:
					value[2] = CCPositionReferenceCornerTopRight
					value[3] = value[4] = CCPositionUnitPoints
				elif posType == kCCBPositionTypeRelativeBottomRight:
					value[2] = CCPositionReferenceCornerBottomRight
					value[3] = value[4] = CCPositionUnitPoints
				elif posType == kCCBPositionTypePercent:
					value[0] /= 100.0
					value[1] /= 100.0
					value[2] = CCPositionReferenceCornerBottomLeft
					value[3] = value[4] = CCPositionUnitNormalized
	
	if posType == kCCBPositionTypePercent:
		if 'animatedProperties' in node:
			for index, prop in node['animatedProperties'].iteritems():
				if 'position' in prop:
					for keyframe in prop['position']['keyframes']:
						keyframe['value'][0] /= 100.0
						keyframe['value'][1] /= 100.0

def convertColor3(node):
	for prop in node['properties']:
		if prop['type'] == 'Color3':
			value = prop['value']
			for i in xrange(len(value)):
				value[i] /= 255.0
			while len(value) < 4:
				value.append(1)

			value = prop.get('baseValue')
			if value is not None:
				for i in xrange(len(value)):
					if value[i] > 1.0:
						value[i] /= 255.0
				while len(value) < 4:
					value.append(1)
	
	if 'animatedProperties' in node:
		for index, prop in node['animatedProperties'].iteritems():
			if 'color' in prop:
				for keyframe in prop['color']['keyframes']:
					value = keyframe['value']
					for i in xrange(len(value)):
						value[i] /= 255.0
					while len(value) < 4:
						value.append(1)

def absoluteSize(node, parentSize):
	sizeProp = None
	for prop in node['properties']:
		if prop['name'] == 'contentSize':
			sizeProp = prop
			break

	if sizeProp is None:
		return [0, 0]
	
	absSize = [0, 0]
	size = sizeProp['value']
	sizeType = sizeProp['value'][2]
	if sizeType == kCCBSizeTypeAbsolute or sizeType == kCCBSizeTypeMultiplyResolution:
		absSize = size[:2]
	elif sizeType == kCCBSizeTypeRelativeContainer:
		absSize[0] = parentSize[0] - size[0]
		absSize[1] = parentSize[1] - size[1]
	elif sizeType == kCCBSizeTypePercent:
		absSize[0] = int(parentSize[0] * size[0] / 100.0)
		absSize[1] = int(parentSize[1] * size[1] / 100.0)
	elif sizeType == kCCBSizeTypeHorizontalPercent:
		absSize[0] = int(parentSize[0] * size[0] / 100.0)
		absSize[1] = size[1]
	elif sizeType == kCCBSizeTypeVerticalPercent:
		absSize[0] = size[0]
		absSize[2] = int(parentSize[1] * size[1] / 100.0)
	
	return absSize

trace = []

def process(parent, parentSize, node):
	try:
		absSize = absoluteSize(node, parentSize)

		stripCCLayer(node)

		convertParticleSystem(node)

		convertAndStripIgnoreAnchorPointForPosition(parent, parentSize, absSize, node)

		convertPosition(node)

		convertColor3(node)

		convertOpacity(node)

		for child in node['children']:
			process(node, absSize, child)
	except Exception:
		klass = node.get('customClass')
		if klass is None or klass == '':
			klass = node.get('baseClass')
		error = '> "%s" of type %s' % (node.get('displayName'), klass)
		if parent is None:
			logging.critical('Node hierarchy:\n' + ', parent of\n'.join(reversed(trace)))
		else:
			trace.append(error)
		raise

if __name__ == '__main__':
	import os
	parser = argparse.ArgumentParser()
	parser.add_argument('files', metavar = 'file', type = str, nargs='+', help = 'A CocosBuilder CCB file to process')
	args = parser.parse_args()

	logging.basicConfig(level = logging.DEBUG)

	for f in args.files:
		logging.info('Processing %s...' % f)
		doc = plistlib.readPlist(f)
		
		process(None, [480, 320], doc['nodeGraph'])

		fileNameParts = os.path.splitext(f)
		newFile = fileNameParts[0] + '-new' + fileNameParts[1]
		plistlib.writePlist(doc, newFile)

		logging.info('Wrote %s' % newFile)
