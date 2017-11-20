#! /usr/bin/python
#
# Simple parser to extract contacts
# Chain ids or TER not required
#
__author__ = "gelpi"
__date__ = "$29-ago-2017 16:14:26$"

from Bio.PDB.NeighborSearch import NeighborSearch
from Bio.PDB.PDBParser import PDBParser
from StructureWrapper import Atom,Residue
from ForceField import VdwParamset
from ResLib import  ResiduesDataLib

import sys
import argparse

COVLNK = 2.0
HBLNK  = 3.5

all_polars = [
    'N', 'ND1', 'ND2', 'NE',  'NE1', 'NE2', 'NH1', 'NH2', 'NZ',
    'O', 'OD1', 'OD2', 'OE1', 'OE2', 'OG',  'OG1', 'OH',
    'S', 'SD',  'SG'
]
backbone_polars =  ['N','O']
waternames = ['WAT','HOH']

def main():

    parser = argparse.ArgumentParser(
                prog='polarContacts',
                description='Polar contacts detector'
            )

    parser.add_argument(
        '--backonly',
        action='store_true',
        dest='backonly',
        help='Restrict to backbone'
    )

    parser.add_argument(
        '--nowats',
        action='store_true',
        dest='nowats',
        help='Exclude water molecules'
    )
    
    parser.add_argument(
        '--diel',
        type= float,
        action='store',
        dest='diel',
        default = 1.0,
        help='Relative dielectric constant'
    )
    
    parser.add_argument(
        '--vdw',
        action='store',
        dest='vdwprm',
        help='VDW Paramters file'
    )
    
    parser.add_argument(
        '--rlib',
        action='store',
        dest='reslib',
        help='AminoAcid library'
    )

    parser.add_argument('pdb_path')

    args = parser.parse_args()

    print ("Settings")
    print ("--------")
    for k,v in vars(args).items():
        print ('{:10}:'.format(k),v)

    backonly = args.backonly
    nowats =args.nowats
    pdb_path = args.pdb_path
    vdwprm = args.vdwprm
    reslib = args.reslib
    diel = args.diel
    
# Load VDW parameters
    vdwParams = VdwParamset(vdwprm)
    print ("{} atom types loaded".format(vdwParams.ntypes))

# Load AA Library
    aaLib = ResiduesDataLib(reslib)
    print ("{} amino acid atoms loaded".format(aaLib.nres))
    
    if not pdb_path:
        parser.print_help()
        sys.exit(2)

    parser = PDBParser(PERMISSIVE=1)

    try:
        st = parser.get_structure('st', pdb_path)
    except OSError:
        print ("#ERROR: loading PDB")
        sys.exit(2)

# Checking for models
    if len(st) > 1:
        print ("#WARNING: Several Models found, using only first")

# Using Model 0 any way
    st = st[0]

# Making a list of polar atoms
    polats = []
    if backonly:
        selected_atoms = backbone_polars
    else:
        selected_atoms = all_polars

    for at in st.get_atoms():
        if at.id in selected_atoms:
            polats.append(at)
#Searching for contacts under HNLNK on diferent residues
    nbsearch = NeighborSearch(polats)
    hblist = []
    for at1, at2 in nbsearch.search_all(HBLNK):
        if at1.get_parent() == at2.get_parent():
            continue
 #Discard covalents and neighbours
        if (at1-at2) < COVLNK:
            continue
        if abs(at2.get_parent().id[1] - at1.get_parent().id[1]) == 1:
            continue
# remove waters
        if nowats:
            if at1.get_parent().get_resname() in waternames \
                or at2.get_parent().get_resname() in waternames:
                continue
                
        atom1 = Atom(at1,1,aaLib,vdwParams)
        atom2 = Atom(at2,1,aaLib,vdwParams)        
        if at1.get_serial_number() < at2.get_serial_number():
            hblist.append([atom1, atom2])
        else:
            hblist.append([atom2, atom1])
       
    print ()
    print ("Polar contacts")
    print ('{:13} {:13} {:6} '.format(
            'Atom1','Atom2','Dist (A)')
    )
    
    for hb in sorted (hblist,key=lambda i: i[0].at.get_serial_number()):
        print ('{:14} {:14} {:6.3f} '.format(
            hb[0].atid(),
            hb[1].atid(),
            hb[0].at - hb[1].at
            )
        )
    print ()
    print ("Residue interactions")

# Making list or residue pairs to avoid repeated pairs
    respairs = []
    for hb in hblist:
        r1 = Residue(hb[0].at.get_parent(), 1, aaLib, vdwParams)
        r2 = Residue(hb[1].at.get_parent(), 1, aaLib, vdwParams)
        if [r1,r2] not in respairs:
            respairs.append([r1,r2])
 
    for rpair in sorted(respairs, key=lambda i: i[0].resNum()):            
        eint = rpair[0].elecInt(rpair[1],diel)
        evdw = rpair[0].vdwInt(rpair[1])
        print (
            '{:10} {:10} {: 8.4f} {: 8.4f} {: 8.4f}'.format(
                rpair[0].resid(), 
                rpair[1].resid(),
                eint,
                evdw,
                eint+evdw)
        )
        
if __name__ == "__main__":
    main()
