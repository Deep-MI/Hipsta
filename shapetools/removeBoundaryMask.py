"""
This module provides a function to remove boundary tetras from tetrahedral meshes

"""

# ------------------------------------------------------------------------------
# AUXILIARY FUNCTIONS

# options_parse()

def options_parse():
    """
    Command Line Options Parser:
    initiate the option parser and return the parsed object
    """

    # imports

    import optparse
    import sys

    # define helptext

    HELPTEXT = """
    SUMMARY

    This is an auxiliary script for the shapetools.py script and is usually
    called from within that script.

    The script requires two arguments:

    --vtk   <file>
    --psol  <file>

    """

    # initialize
    parser = optparse.OptionParser(usage=HELPTEXT)

    # help text
    h_vtk = 'vtk file'
    h_psol = 'psol file'

    # specify inputs
    group = optparse.OptionGroup(parser, "Required Options:", "...")
    group.add_option('--vtk', dest='vtk', help=h_vtk)
    group.add_option('--psol', dest='psol', help=h_psol)
    parser.add_option_group(group)

    # parse arguments
    (options, args) = parser.parse_args()

    # check if there are any inputs
    if len(sys.argv)==1:
        print(HELPTEXT)
        sys.exit(0)

    # check if vtk file is given
    if options.vtk is None:
        print('\nERROR: Specify --vtk\n')
        sys.exit(1)
    else:
        print('... Found vtk file '+options.vtk)

    # check if psol file is given
    if options.psol is None:
        print('\nERROR: Specify --psol\n')
        sys.exit(1)
    else:
        print('... Found psol file '+options.psol)

    # return
    return options


# -----------------------------------------------------------------------------
# MAIN FUNCTION

def removeBoundaryMask(params, VTKFile=None, PSOLFile=None, labelBndHead=2320, labelBndTail=2260):

    # -------------------------------------------------------------------------
    # imports

    import os

    import numpy as np

    import lapy as lp
    from lapy import TriaIO as lpio
    from lapy import TetIO as lptio
    from lapy import FuncIO as lpfio

    # -------------------------------------------------------------------------
    # message

    print()
    print("-------------------------------------------------------------------")
    print()
    print("Removing boundary tetras from mesh")
    print()
    print("-------------------------------------------------------------------")
    print()

    # -------------------------------------------------------------------------
    # evaluate input

    if params is not None:
        VTKFile = os.path.join(params.OUTDIR, params.HEMI + "." + params.internal.HSFLABEL_07 + ".vtk")
        PSOLFile = os.path.join(params.OUTDIR, "tetra-labels", params.HEMI + "." + params.internal.HSFLABEL_07 + ".psol")

    # -------------------------------------------------------------------------
    # determine values

    if params is not None:

        labelBndHead = params.LUTDICT['bndhead']
        labelBndTail = params.LUTDICT['bndtail']

    # -------------------------------------------------------------------------
    # load data

    tetMesh = lptio.import_vtk(VTKFile)

    l = lpfio.import_vfunc(PSOLFile)
    l = np.array(l)

    vTail = tetMesh.v[l==labelBndTail, ]
    vHead = tetMesh.v[l==labelBndHead, ]

    # -------------------------------------------------------------------------
    # cutting surfaces based on point-cloud PCA

    vTaile, vTailc = np.linalg.eig(np.cov(vTail, rowvar=False))
    vHeade, vHeadc = np.linalg.eig(np.cov(vHead, rowvar=False))

    # need to order EVs

    vTailc = vTailc[:, np.flip(np.argsort(vTaile), axis=0)]
    vHeadc = vHeadc[:, np.flip(np.argsort(vHeade), axis=0)]
    vTaile = np.flip(np.sort(vTaile), axis=0)
    vHeade = np.flip(np.sort(vHeade), axis=0)

    vTails = np.linalg.solve(vTailc, (vTail - np.mean(vTail, axis=0)).T).T
    vHeads = np.linalg.solve(vHeadc, (vHead - np.mean(vHead, axis=0)).T).T

    # -------------------------------------------------------------------------
    # determine on which side of the plane a given point is

    # head

    # support vectors (move a little bit inwards, direction may differ); first,
    # determine if the richtungsvektor is pointing towards the center:

    if np.linalg.norm( (np.mean(tetMesh.v, axis=0) - np.mean(vHead, axis=0)) ) > np.linalg.norm( np.mean(tetMesh.v, axis=0) - (np.mean(vHead, axis=0) + vHeadc[:, 2]) ): # yes
        sHead   = np.mean(vHead, axis=0) + 1.0 * vHeadc[:, 2]
        dirHead = 1
    else:
        sHead   = np.mean(vHead, axis=0) - 1.0 * vHeadc[:, 2]
        dirHead = 0

    # compute unit normal vector to plane

    uHead = vHeadc[:,2] / np.linalg.norm(vHeadc[:,2])

    # compute normals from each point to plane (could be v or vHead)

    dHead = np.zeros(tetMesh.v.shape[0])

    for i in range(0, tetMesh.v.shape[0]):

        # vector from point to support vector
        n = tetMesh.v[i, :] - sHead

        # distance from point to plane along normal
        dHead[i] = np.dot(n, uHead)

    # tail

    # support vectors (move a little bit inwards, direction may differ); first,
    # determine if the richtungsvektor is pointing towards the center:

    if np.linalg.norm( (np.mean(tetMesh.v, axis=0) - np.mean(vTail, axis=0)) ) > np.linalg.norm( np.mean(tetMesh.v, axis=0) - (np.mean(vTail, axis=0) + vTailc[:, 2]) ):
        sTail   = np.mean(vTail, axis=0) + 1.0 * vTailc[:, 2] # yes
        dirTail = 1
    else:
        sTail   = np.mean(vTail, axis=0) - 1.0 * vTailc[:, 2] # no
        dirTail = 0

    # compute unit normal vector to plane

    uTail = vTailc[:, 2] / np.linalg.norm(vTailc[:, 2])

    # compute normals from each point to plane (could be v or vTail)

    dTail = np.zeros(tetMesh.v.shape[0])

    for i in range(0, tetMesh.v.shape[0]):

        # vector from point to support vector
        n = tetMesh.v[i, :] - sTail

        # distance from point to plane along normal
        dTail[i] = np.dot(n, uTail)

    # -------------------------------------------------------------------------
    # remove triangles that contain 2 or 3 or 4 points

    if dirHead & dirTail:
        tcut = tetMesh.t[np.sum(np.reshape(np.in1d(tetMesh.t, np.where((dTail <= 0)|(dHead <= 0))), tetMesh.t.shape), axis=1) < 2, :]
        vcutIdxTail = np.where(dTail <= 0)[0]
        vcutIdxHead = np.where(dHead <= 0)[0]
    elif (not(dirHead)) & dirTail :
        tcut = tetMesh.t[np.sum(np.reshape(np.in1d(tetMesh.t, np.where((dTail <= 0)|(dHead  > 0))), tetMesh.t.shape), axis=1) < 2, :]
        vcutIdxTail = np.where(dTail <= 0)[0]
        vcutIdxHead = np.where(dHead  > 0)[0]
    elif dirHead & (not(dirTail)) :
        tcut = tetMesh.t[np.sum(np.reshape(np.in1d(tetMesh.t, np.where((dTail  > 0)|(dHead <= 0))), tetMesh.t.shape), axis=1) < 2, :]
        vcutIdxTail = np.where(dTail  > 0)[0]
        vcutIdxHead = np.where(dHead <= 0)[0]
    elif (not(dirHead)) & (not(dirTail)) :
        tcut = tetMesh.t[np.sum(np.reshape(np.in1d(tetMesh.t, np.where((dTail  > 0)|(dHead  > 0))), tetMesh.t.shape), axis=1) < 2, :]
        vcutIdxTail = np.where(dTail  > 0)[0]
        vcutIdxHead = np.where(dHead  > 0)[0]

    # -------------------------------------------------------------------------
    # remove empty vertices

    fcutRenum = np.digitize(tcut, np.unique(tcut), right=True)
    vcutRenum = tetMesh.v[np.unique(tcut), ]

    # -------------------------------------------------------------------------
    # write PSOL

    vIdx = np.zeros(np.shape(tetMesh.v)[0])
    vIdx[vcutIdxHead] = labelBndTail
    vIdx[vcutIdxTail] = labelBndHead

    lpfio.export_vfunc(os.path.join(params.OUTDIR, "tetra-cut", params.HEMI + "." + params.internal.HSFLABEL_07 + "_tetra-remove" + ".psol"), vIdx)

    # for visualization

    tetMeshBnd = tetMesh.boundary_tria()

    vRmBndKeep, vBndRmDel = tetMeshBnd.rm_free_vertices_()

    tetMeshBnd.orient_()

    lpio.export_vtk(tria=tetMeshBnd, outfile=os.path.join(params.OUTDIR, "tetra-cut", params.HEMI + ".rm.bnd." + params.internal.HSFLABEL_07 + ".vtk"))

    lpfio.export_vfunc(os.path.join(params.OUTDIR, "tetra-cut", params.HEMI + ".rm.bnd." + params.internal.HSFLABEL_07 + ".psol"), vIdx)

    # -------------------------------------------------------------------------
    # update params

    params.internal.HSFLABEL_08 = "rm." + params.internal.HSFLABEL_07

    # -------------------------------------------------------------------------
    # return

    return params


# -----------------------------------------------------------------------------
# CLI

if __name__=="__main__":

    # command-line options and error checking

    options = options_parse()

    # run main function

    removeBoundaryMask(params=None, VTKFile=options.vtk, PSOLFile=options.psol)
