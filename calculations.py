'''
File includes all of the necessary code to perform calculations and
return necessary values for each step in the automation process

The classes are setup to accept dictionary argument passing read the
help() on each class to understand what you need to pass in order to
ensure correct operation

upon calling the class, it returns the appropriate values upon which
it has been asked to return.

*Essentially it is a function*
'''
import math, pprint

import errorCheck as b_PyError
import parsing as b_PyParse
import numpy
import copy # needed for deepcopy of arrays
import collections

from collections import OrderedDict as orderedDict
from config import BERRY_DEFAULT_CONSOLE_PREFIX as DEFAULT_PREFIX
from convunits import bohrToMeters # conversion [Bohr] => [m]

DEBUG = True


##################
# default values #
##################

ELECTRON_CHARGE = 1.60217646e-19
#bohr to meters
BOHR_CONSTANT = 5.2917725e-11

#value which determines the bounds 
#of zeroing our 2pi values
GAMMA_ZEROING_VALUE = 0.1

COORDINATE_CORRECTION_UPPER_BOUND = 1.0
COORDINATE_CORRECTION_LOWER_BOUND = 0.8

class PathphaseCalculation:
	'''
	-- arguments --

	values(list) : list of berry phase values which you wish to pass
	to the calculation


	'''
	def __init__(self, **args):
		self.topDomain = math.pi * 2
		self.values = args['values']
		self.correctDomain() #produces correct domain in self.correctedValues
		self.meanValue = (sum(self.correctedValues) / len(self.correctedValues)) / (self.topDomain/2)
		#	print self.meanValue
	

	def correctDomain(self):
		'''
		Correct the domain of the pathphase values so that they lie
		within the [0, 2PI] domain -- [0. 6.28]
		'''
		def correctPhaseDomain(phaseValue):
			'''
			Corrects the values phase so that it resides 
			between topDomain and bottomDomain
			'''
			topDomain = 1.
			bottomDomain = -1.

			domainRange = topDomain - bottomDomain

			phaseValue %= domainRange
			if phaseValue >= topDomain or phaseValue <= bottomDomain:
				if phaseValue > 0:
						phaseValue -= domainRange
				elif phaseValue <= 0:
				    phaseValue += domainRange
			return phaseValue

		topDomain = self.topDomain

		self.consistentDomainValues = self.values[:]
		self.consistentDomainValues2 = self.values[:]
		#use modulo 2PI to maintain a consistent domain
		self.consistentDomainValues = [ (i + (2 *numpy.pi)) % topDomain for i in self.consistentDomainValues]


		self.consistentDomainValues2 = [ correctPhaseDomain(i) for i in self.consistentDomainValues2]

		self.correctedValues=numpy.unwrap(self.consistentDomainValues)
		self.correctedValues2=numpy.unwrap(self.consistentDomainValues2)
        
	def getValues(self):
		return self.values

	def getCorrectedValues(self):
		return self.correctedValues
	def getCorrectedValues2(self):
		return self.correctedValues2

	
	def getMeanValue(self):
		return self.meanValue

	def getConsistentDomainValues(self):
		return self.consistentDomainValues
	def getConsistentDomainValues2(self):
		return self.consistentDomainValues2

		

class CalculateNumberOfBands:
    '''
    Used to calculate the number of bands within the *.scf file to
    determine the input for the write_w2win function.

    You pass a file path to the *.scf in order to carry out this
    calculation
    '''
    def __init__(self, filePath):
        self.text = open(filePath, 'r').readlines()
        self.parser = b_PyParse.MainSCFParser(self.text)
        self.parser.parse()

    def getNumberOfBands(self):
        bandList = self.parser['Band List']
        #produce list from dictionary values with only the occupancy
        #and band range where occupancy is not 0
        theList = [ (i['band range'], i['occupancy']) for i in bandList if i['occupancy'] ]
        # return the last occupancy
        return theList[-1][0]

    
        

class MainCalculationContainer:
    '''
    This class contains every calculation and spits out the final result

    -- arguments --
    phasesRaw[ direction(x/y/z), spin , k-path , initial k-point , phase(rad) ] - list with phases
    
    spCalc - identifier for spin polarized calculation: True - sp, False - no sp

    file_struct(file path) - to structure .struct file

    file_scf(file path) - to .scf file

    file_outputd(file path) - to .outputd file

    file_outputst(file path) - to .outputst file
    '''
    def __init__(self, **args):

        # spin polarization: yes/no
        spCalc = args['sp']

        ############################
        ######### PARSING ##########
        ############################

        ###Rest of the Files###
        #parse all the things!
        #### *.struct file parser
        parser_struct_handle = open(args['file_struct'], 'r').readlines()
        parser_struct_handle = b_PyParse.MainStructParser(parser_struct_handle)
        parser_struct_handle.parse()


        #### *.scf file parser
        parser_scf_handle = open(args['file_scf'], 'r').readlines()
        parser_scf_handle = b_PyParse.MainSCFParser(parser_scf_handle)
        parser_scf_handle.parse()


        #### *.outputd parser
        parser_outputd_handle = open(args['file_outputd'], 'r').readlines()
        parser_outputd_handle = b_PyParse.MainOutputDParser(parser_outputd_handle)
        parser_outputd_handle.parse()

        
        #### *.outputst parser
        parser_outputst_handle = open(args['file_outputst'], 'r').readlines()
        parser_outputst_handle = b_PyParse.MainOutputstParser(parser_outputst_handle)
        parser_outputst_handle.parse()


        #####################################
        ############ END Parsing ############
        #####################################


        #############################
        ###### Getting Values #######
        #############################
        self._calculationValues = orderedDict();
        
        #### *.struct handle
        # - determine name of atoms
        # - determine MULT for each atom
        self._calculationValues['Atom Listing'] = \
            parser_struct_handle['Atom Listing'];
        
        #### *.scf handle
        # - Cell Volume
        self._calculationValues['Cell Volume in bohr^3'] = \
            parser_scf_handle['Cell Volume'];
        self._calculationValues['Cell Volume in m^3'] = \
            bohrToMeters(self._calculationValues['Cell Volume in bohr^3'],3);

        #### *.outputd handle
        # - BR2_DIR matrix (v_x, v_y, v_z)
        # - number of atoms in cell
        # - Lattice Constants (x,y,z)
      	laticematrix=parser_outputd_handle['BR2_DIR Matrix']
      	latticematrixa1=laticematrix[0]
      	self._calculationValues['Lattice Matrix a1 in bohr'] = \
            latticematrixa1;
      	latticematrixa2=laticematrix[1]
      	self._calculationValues['Lattice Matrix a2 in bohr'] = \
            latticematrixa2;
      	latticematrixa3=laticematrix[2]
      	self._calculationValues['Lattice Matrix a3 in bohr'] = \
            latticematrixa3;
        self._calculationValues['Lattice Matrix in bohr'] = \
            parser_outputd_handle['BR2_DIR Matrix'];
        self._calculationValues['Lattice Matrix in m'] = \
            [[ bohrToMeters(i) for i in j ] for j in \
            self._calculationValues['Lattice Matrix in bohr']];
        self._calculationValues['Number of Atoms in Unit Cell'] = \
            parser_outputd_handle['Number of Atoms in Unit Cell'];
        self._calculationValues['Lattice Constants in bohr'] = \
            parser_outputd_handle['Lattice Constants'];
        self._calculationValues['Lattice Constants in m'] = \
            [ bohrToMeters(i) for i in \
            self._calculationValues['Lattice Constants in bohr']];

        #### *.outputst handle
        # for each element:
        # - Core Value
        # - Spin Value 1
        # - Spin Value 2
        self._calculationValues['Element Listing'] = \
            parser_outputst_handle['Element List'];

        ####
        
        ########################
        # get electronic phase #
        ########################
        # get raw list [k-points, phase]
        phaseDirSpinPathRaw = args['phases']
        # wrap phases in the range [-pi ... +pi]
        phaseDirSpinPathWrp11 = self.wrpPhase(phaseDirSpinPathRaw, \
            self.wrp11);
        # print nice
        print "\n","Initial Berry phases and their", \
            "wrapped values in the range [-pi ... +pi]";
        print "="*87
        print " "*30, "| init k-point", "| phase raw (rad)", \
            "| phase wrap. (rad)"
        icoord = -1
        for coord in phaseDirSpinPathRaw:
            icoord += 1
            print "-"*87
            print "direction(%u)" % int(icoord + 1)
            ispin = -1
            for spin in coord:
                ispin += 1
                print " "*12, "spin(%u)" % int(ispin + 1)
                ipath = -1
                for path in spin:
                    ipath += 1
                    # perform wraping using the method privided in input
                    kpt = phaseDirSpinPathRaw[icoord][ispin][ipath][0]
                    ph = phaseDirSpinPathRaw[icoord][ispin][ipath][1]
                    phwrp = phaseDirSpinPathWrp11[icoord][ispin][ipath][1]
                    print " "*20, "path(%4d)       %4d        % e        % e" \
                        % (ipath+1, kpt, ph, phwrp)
        print "="*87
        print "\n","CALCULATION OF ELECTRONIC POLARIZATION"
        print "="*87
        print "Value", " "*25, "|  spin  ", "|   ", "dir(1)   ", \
            "|   ", "dir(2)   ", "|   ", "dir(3)"
        print "-"*87
        # find path-average phase
        phaseDirSpinWrp11 = self.pathAvrgPhase(phaseDirSpinPathWrp11);
        # wrap the average phase again as it can go out of bounds [-pi..+pi]
        phaseDirSpinWrp11 = self.wrp11(phaseDirSpinWrp11);
        nspins = numpy.shape(phaseDirSpinWrp11)[1]
        for spinIndex in range(0,nspins):
            print "Berry phase (rad) [-pi ... +pi]    sp(%1i)" \
                % (spinIndex+1), \
                " [% e, % e, % e]" % tuple(phaseDirSpinWrp11[:,spinIndex]);                
        if not spCalc and not args['so']: # in case of non-SP or non-SO calculation...
            phaseDirSpinWrp11 = 2*phaseDirSpinWrp11 # account for the spin degeneracy
            nspins = numpy.shape(phaseDirSpinWrp11)[1]
            if nspins != 1: # double check
                print "Inconsistency detected in the number of spins"
                print "Is it spin-polarized calculation? spCalc =", spCalc
                print "Number of spins in the electronic phase array", \
                    nspins;
                print "Expected 1 spin"
                print "Decision is taken to EXIT"
                sys.exit(2)
            print "Berry phase (rad)                  up+dn  "+ \
                "[% e, % e, % e]" % tuple(phaseDirSpinWrp11);
            # wrap phases again [-pi ... +pi]
            phaseDirSpinWrp11 = self.wrp11(phaseDirSpinWrp11)
            print "Berry phase (rad) [-pi ... +pi] " +\
                "   up+dn  [% e, % e, % e]" \
                % tuple(phaseDirSpinWrp11);
        #electron charge / cell volume
        self.ELEC_BY_VOL_CONST = ELECTRON_CHARGE / \
            bohrToMeters(self._calculationValues['Cell Volume in bohr^3'], \
            dimension = 3.);
        # electronic polarization (C/m2)
        elP = self.elPolarization(phaseDirSpinWrp11,self._calculationValues, \
            self.ELEC_BY_VOL_CONST);
        # ionic polarization (C/m2)
        ionP = self.determineIonPolarization(self.wrp11,args)
        # Total polarization (C/m2) will be returned
        # when calling mainCalculation()
        self._totalPolarizationVal = self.totalPolarization(elP, ionP)
        # END main


    def wrpPhase(self, List, fnWrpMethod):
        # wrap phases from a List and bring them in the interval
        # [-pi..+pi]
        # List = [direction(x/y/z), spin, k-path, [start k-point, phase]]
        #                                                           ^
        #                                                        unwrapped
        # fnWrpMethod - function that determines the method
        #
        # OUT = [direction(x/y/z), spin, k-path, [start k-point, phase]]
        #                                                           ^
        #                                                        wrapped
        OUT = copy.deepcopy(List) # initialize output list
                                  # deepcopy helps to avoid unintentional
                                  # modification of the input arguments
                                  # (stupid python)
        icoord = -1
        for coord in List:
            icoord = icoord + 1
            ispin = -1
            for spin in coord:
                ispin = ispin + 1
                ipath = -1
                for path in spin:
                    ipath = ipath + 1
                    # perform wraping using the method provided in input
                    OUT[icoord][ispin][ipath][1] \
                        = fnWrpMethod( List[icoord][ispin][ipath][1] )
                pathPhaseWrp = OUT[icoord][ispin][:,1]
                # unwrap phases among all pathes for a particular spin
                # for example [-pi, +pi] => [-pi, -pi]
                pathPhaseUnwrp = numpy.unwrap( pathPhaseWrp )
                OUT[icoord][ispin][:,1] = pathPhaseUnwrp
        return OUT

    def wrp11(self, IN):
        # wraps phase into the range [-pi .. +pi]
        # IN can be any array of phases in (rad)
        x = IN/numpy.pi # it will be easier to work with numbers [-1..+1]
        # apply to all elements of the array
        inisarray = isinstance(x, (numpy.ndarray));
        if inisarray: # check if input is an array
            inshape = x.shape
            x = x.flatten() # flaten input array into 1D vector
                            # need for compatibility with NumPy 1.9.2
        # do wrapping [-1..+1]
        absx = numpy.absolute(x);
        y = numpy.piecewise(x, [absx > 1], \
            [lambda x: x + numpy.sign((-1)*numpy.array(x))* \
                       numpy.round(numpy.absolute(x)/2)*2, \
             lambda x: x]);
            # last 'x' is needed as _else_ condition
            # (i.e., no change in x)
        OUT = y*numpy.pi # get back to radians [-pi..+pi]
        if inisarray: # restore output array dimensions to match input
            OUT.resize(inshape)
        return OUT


    def pathAvrgPhase(self, List):
        # calculate path-average phase 
        # List = [direction(x/y/z), spin, k-path, [start k-point, phase]]
        #
        # OUT = average phase[direction(x/y/z), spin]
        # allocate output array based on number of directions and spins
        nspins = numpy.shape(List[0])[0]
        OUT = numpy.zeros((3,nspins)) # 3 spece directions X num. spins
        icoord = -1
        for coord in List:
            icoord = icoord + 1
            ispin = -1
            for spin in coord:
                ispin = ispin + 1
                ipath = -1
                x = 0
                for path in spin:
                    ipath = ipath + 1
                    x =  x + List[icoord][ispin][ipath][1]
                avrg = x/(ipath+1)
                OUT[icoord][ispin] = avrg
        return OUT



    def getPhasevalues(self):
		return self.phaseValues

    def getPhaseConsistentDomainValues(self):
		return self.value_phaseConsistentDomainValues
    def getPhaseConsistentDomainValues2(self):
		return self.value_phaseConsistentDomainValues2


    def getPhaseCorrectedValues(self):
		return self.value_phaseCorrectedValues
    def getPhaseCorrectedValues2(self):
		return self.value_phaseCorrectedValues2


    def valuephaseMeanValues(self):
		return self.value_phaseMeanValues

    def __call__(self):
        return self.totalPolarizationVal()

    def calculationValues(self):
        return self._calculationValues

    def prettyPrintCalculationValues(self):
        pprint.pprint(self._calculationValues)
    
    def elPolarization(self, berryPhase, calcValues, ELEC_BY_VOL_CONST):
        '''
        Calculate electronic component of polarization

        Input: berryPhase[direction 1, 2, 3][spin]

        Calculation:

        Pel_x = electron charge / unit volume (m) * \
          berry phase mean value/2pi * lattice_matrices (diagonal x);
        '''
        latticeConstants = calcValues['Lattice Constants in bohr']
        latticeMatrix_x = calcValues['Lattice Matrix in bohr'][0]
        latticeMatrix_y = calcValues['Lattice Matrix in bohr'][1]
        latticeMatrix_z = calcValues['Lattice Matrix in bohr'][2]
        # return the absolute value of the vector sqrt(x^2 + y^2 + z^2)
        absVector = lambda vec: math.sqrt(sum([i**2 for i in vec]))
        # length of lattice vectors
        lattice_x = absVector(latticeMatrix_x)
        lattice_y = absVector(latticeMatrix_y)
        lattice_z = absVector(latticeMatrix_z)
	      # Electronic Polarization [OLEG]: check which lattice constants to use
        nspins = numpy.shape(berryPhase)[1]
        elP = numpy.zeros((nspins,3))
        for spinIndex in range(0,nspins):
            for coordIndex in range(0,3):
                elP[spinIndex,coordIndex] = \
                    (berryPhase[coordIndex,spinIndex]/(2*numpy.pi)) * \
                    ELEC_BY_VOL_CONST * \
                    bohrToMeters(latticeConstants[coordIndex]);
            print "Electronic polarization (C/m2)     " +\
                "sp(%1i) " % (spinIndex+1), \
            "[% e, % e, % e]" % tuple(elP[spinIndex,:]);
        print "="*87
        return elP; # END elPolarization

    # [OLEG] check if any old functions left to be removed
    #Electron polrization in [0 to 2] range
    def electronpolar2pi(self):
		return self._electronpolar2pi


#Berry/electronic phase in [-1 to +1] range  
    def remappedberryphase(self):	
		return self._berryremapped	

    def ebyVlatticeconstant(self):		
		return self._ebyVandlatticeconstant	


#Electron polrization in [-1 to +1 range]
    def electronPolarization(self):
        return self._electronPolarization

    # Ionic polarization
    def determineIonPolarization(self, fnWrpMethod, args):
        '''
        INPUT: fnWrpMethod - function that determines the method for
                             wrapping the phase
               args - contains logical variables regarding the
                      calculation setup
                      args['so'] - spin-orbit coupling
                      args['sp'] - spin-polarized calculation
                      args['orb'] - additional orbital potential (LDA+U)

        Calculation:

        Pion_x = electron charge / unit volume (m) * lattice_x * (
        
          sum of (
            atom valence charge * position(x)
            )
          )

          where atom valence charge = ( core value - spin val 1 - spin val 2 )
        '''
        print "\n", "CALCULATION OF IONIC POLARIZATION"
        ionP = []
        calcValues = self.calculationValues()
        ELEC_BY_VOL_CONST = self.ELEC_BY_VOL_CONST
        latticeConstants = calcValues['Lattice Constants in bohr']
        atomListing = calcValues['Atom Listing']
        #produce a tuple pair which includes the valence electrons and
        #the coordinates for each element
        calcIonValues = [] # (coordinates(x,y,z), valence value)
        
        #TODO: include good exception handling for this stage
        #construct the calcIonValues for the calculation
        if args['sp'] and not args['so']:
            nspins = 2
        else:
            nspins = 1
        for atom in atomListing:
            for i in range(atom['MULT']):
                theElementName = atom['Element Name']
                if calcValues['Element Listing'].has_key(theElementName):
                    theElement = calcValues['Element Listing'][theElementName]
                    if nspins == 2:
                        theValence = []
                        for spin in [1, 2]:
                            theValence.append( \
                                atom['Znucl']/2 - theElement['Core Value']/2 \
                            );
                    else:
                        theValence = atom['Znucl'] - theElement['Core Value'];
                    xCoordinate = atom['X-Coord'][i]
                    yCoordinate = atom['Y-Coord'][i]
                    zCoordinate = atom['Z-Coord'][i] 

                    #produce tuple from coordinates
                    coordinates = (xCoordinate, yCoordinate, zCoordinate)
                    calcIonValues.append((theElementName,coordinates, theValence))
                else:
                    print DEFAULT_PREFIX + 'ERROR: Missing element in element list'
                    print DEFAULT_PREFIX + theElementName
                    print DEFAULT_PREFIX + calcValues['Element List']
                    print DEFAULT_PREFIX + 'Exiting....'
                    sys.exit(1)
        self._calcIonValues = calcIonValues

        #### CALCULATION ####
        xPolarIon, yPolarIon, zPolarIon = (0., 0., 0.)
        print "="*87
        print "Elem.|  Fractional coord.  |  spin | Zion |", \
            "   dir(1)   ", \
            "|   ", "dir(2)   ", "|   ", "dir(3)"
        print "-"*87
        print " "*41, "+"+"-"*12, "Ionic phase (rad)", \
            "-"*12+"+"
        totIonPhase = numpy.zeros((nspins,3))
        for element, iCoord, iValence in calcIonValues:
            spinIndex = -1
            if isinstance(iValence, collections.Iterable):
                pass
            else:
                iValence = [iValence, ]
            for spinValence in iValence:
                spinIndex += 1
                ionPhase = numpy.zeros((nspins,3))
                coordIndex = -1
                for fcoord in iCoord:
                    coordIndex += 1
                    # fractional coordinates used
                    psi = fcoord * spinValence * 2*numpy.pi
                    ionPhase[ spinIndex , coordIndex ] = psi
                if spinIndex == 0:
                    print "%2s " % element, \
                        "(%6.4f, %6.4f, %6.4f) " % iCoord, \
                        "sp(%1i)" % (spinIndex+1), \
                        "%5.2f" % spinValence, \
                        "[% e, % e, % e]" % tuple(ionPhase[spinIndex,:]);
                else:
                    print " "*29, \
                        "sp(%1i)" % (spinIndex+1), \
                        "%5.2f" % spinValence, \
                        "[% e, % e, % e]" % tuple(ionPhase[spinIndex,:]);
                totIonPhase[:,:] += ionPhase
        print "-"*87
        for spinIndex in range(0,nspins):
           	print "Total ionic phase (rad)", " "*5, \
                "sp(%1i)" % (spinIndex+1), " "*5, \
                "[% e, % e, % e]" % tuple(totIonPhase[spinIndex,:]);

        # warap phases
        totIonPhase = fnWrpMethod( totIonPhase );

        for spinIndex in range(0,nspins):
           	print "Total ionic phase wrap. (rad)", \
                "sp(%1i)" % (spinIndex+1), " "*5, \
                "[% e, % e, % e]" % tuple(totIonPhase[spinIndex,:]);

        #IONIC Polarization
        ionPol = numpy.zeros((nspins,3))
        for spinIndex in range(0,nspins):
            for coordIndex in range(0,3):
                psi = totIonPhase[spinIndex,coordIndex]
                a = latticeConstants[coordIndex]
                ionPol[spinIndex,coordIndex] = \
                    (psi/(2*numpy.pi)) * ELEC_BY_VOL_CONST * \
                    bohrToMeters(a);
            print "Ionic polarization (C/m2)    ", \
                "sp(%1i)" % (spinIndex+1), " "*5, \
                "[% e, % e, % e]" % tuple(ionPol[spinIndex,:]);
        print "="*87

        return ionPol # END determineIonPolarization

#Valance Electron
    def valance(self):
	return self._calcIonValues


#Ionic Phase in 2Pi modulo 
    def ionicphase(self):
	return self._ionicphase
   

#Ionic Phase in [-1 to +1] range
    def mappedionic(self):
	return self._mappedionic

#Ionic Polrization in [0 to 2] range

    def ionicpolar2pi(self):
	return self._ionicpolar2pi
#Ionic Polarization in [-1 to +1] range
    def ionPolarization(self):
        return self._ionPolarization




    def correctPhaseDomain(self,phaseValue):
        '''
        Corrects the values phase so that it resides 
        between topDomain and bottomDomain
        '''
        topDomain = 1.
        bottomDomain = -1.

        domainRange = topDomain - bottomDomain

	phaseValue %= domainRange
        if phaseValue >= topDomain or phaseValue <= bottomDomain:
	        if phaseValue > 0:
				phaseValue -= domainRange
	        elif phaseValue <= 0:
	            phaseValue += domainRange
        return phaseValue	

    # Total polarization
    def totalPolarization(self, elP, ionP):
        '''
        Calculate total polarization
        INPUT: elP    - electronic polarization (C/m2)
               ionP   - ionic polarization (C/m2)
        OUTPUT: totP  - total polarization (C/m)
                totP = elP + ionP
        '''
        totSpinP = numpy.add(elP, ionP)
        nspins = numpy.shape(totSpinP)[0]
        print "\nSUMMARY OF POLARIZATION CALCULATION"
        print "="*87
        print "Value", " "*25, "|  spin  ", "|   ", "dir(1)   ", \
            "|   ", "dir(2)   ", "|   ", "dir(3)"
        for spinIndex in range(0,nspins):
            print "-"*87
            print "Electronic polarization (C/m2)     " + \
                "sp(%1i) " % (spinIndex+1), \
                "[% e, % e, % e]" % tuple(elP[spinIndex,:])
            print "Ionic polarization (C/m2)          " + \
                "sp(%1i) " % (spinIndex+1), \
                "[% e, % e, % e]" % tuple(ionP[spinIndex,:])
            print "Tot. spin polariz.=Pion+Pel (C/m2) " + \
                "sp(%1i) " % (spinIndex+1), \
                "[% e, % e, % e]" % tuple(totSpinP[spinIndex,:])
        print "-"*87
        totP = numpy.sum(totSpinP, axis=0) # summ over spins
        print "TOTAL POLARIZATION (C/m2)          " + \
            "both   [% e, % e, % e]" % tuple(totP)
        print "="*87
        return totP # END totalPolarization

#Total Phase [0 to 2] range
    def totalphase2pi(self):
	return self._totalphase2pi

#Total Phase [+1 to -1] range

    def totalphaseneg1to1(self):
	return self._totalphaseneg1to1	


#Total Polarization [-1 to +1] range
    def totalPolarizationVal(self):
        return self._totalPolarizationVal


#Total Polarization [0 to 2] range
    def netpolarization2pi(self):
	return self._netPolarizationEnergy1


        
if __name__ == "__main__":

    mainCalculation = MainCalculationContainer(
        file_pathphase_x = './tests/testStruct-x.pathphase',
        file_pathphase_y = './tests/testStruct-x.pathphase',
        file_pathphase_z = './tests/testStruct-x.pathphase',
        file_struct = './tests/testStruct.struct',
        file_scf = './tests/testStruct.scf',
        file_outputd = './tests/testStruct.outputd',
        file_outputst = './tests/testStruct.outputst',
        )
    mainCalculation.prettyPrintCalculationValues()
    print mainCalculation.valuephaseMeanValues()
    print mainCalculation.electronpolar2pi()
    print mainCalculation.remappedberryphase
    print mainCalculation.electronPolarization()
    print mainCalculation.ionicphase()	
    print mainCalculation.ionicpolar2pi()
    print mainCalculation.mappedionic()
    print mainCalculation.ionPolarization()
    print mainCalculation.totalphase2pi()
    print mainCalculation.totalphaseneg1to1()
    print mainCalculation.netPolarizationEnergy()
    print mainCalculation.netpolarization2pi()
    print mainCalculation.valance()	 
    print mainCalculation()
    blochBandCalculation = CalculateNumberOfBands('./tests/testStruct.scf')
