# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

# ----------------------------------------------------------------------------
import struct
import ctypes
import colorsys
import random
import bpy
import bmesh


# ----------------------------------------------------------------------------
CPJ_HDR_RIFF_MAGIC = struct.unpack("I", b"RIFF")[0]
CPJ_HDR_FORM_MAGIC = struct.unpack("I", b"CPJB")[0]

CPJ_FRM_MAGIC = "FRMB"
CPJ_FRM_VERSION = 1
CPJ_GEO_MAGIC = "GEOB"
CPJ_GEO_VERSION = 1
CPJ_LOD_MAGIC = "LODB"
CPJ_LOD_VERSION = 3
CPJ_MAC_MAGIC = "MACB"
CPJ_MAC_VERSION = 1
CPJ_SEQ_MAGIC = "SEQB"
CPJ_SEQ_VERSION = 1
CPJ_SKL_MAGIC = "SKLB"
CPJ_SKL_VERSION = 1
CPJ_SRF_MAGIC = "SRFB"
CPJ_SRF_VERSION = 1


# ----------------------------------------------------------------------------
def load(context, filepath):

    # info
    print("Reading %s..." % filepath)

    # open and read file
    with open(filepath, mode="rb") as handle:
        data = handle.read()

        # unsigned long riffMagic; // CPJ_HDR_RIFF_MAGIC
        # unsigned long lenFile; // length of file following this value
        # unsigned long formMagic; // CPJ_HDR_FORM_MAGIC
        SCpjFileHeader = struct.unpack_from("III", data, 0)

        if (SCpjFileHeader[0] != CPJ_HDR_RIFF_MAGIC
                or SCpjFileHeader[2] != CPJ_HDR_FORM_MAGIC):
            raise ImportError("This file is not a CPJ file")

        if SCpjFileHeader[1] != len(data) - 8:
            raise ImportError("File has wrong size, propably corrupted")

        # compatibility flags
        bl_object = None
        has_surface_already = False

        # chunks order workaround
        # loop 0: MAC
        # loop 1: GEO
        # loop 2: SRF
        # loop 3: rest
        for loop in range(4):

            # skip file header
            idx = 12

            # loop over all chunks
            while idx < len(data):

                # unsigned long magic; // chunk-specific magic marker
                # unsigned long lenFile; // length of chunk following this value
                # unsigned long version; // chunk-specific format version
                # unsigned long timeStamp; // time stamp of chunk creation
                # unsigned long ofsName; // offset of chunk name string from start of chunk
                #                        // If this value is zero, the chunk is nameless
                SCpjChunkHeader = struct.unpack_from("IIIII", data, idx)

                # decode chunk type
                magic = data[idx:idx + 4].decode()
                version = SCpjChunkHeader[2]

                if SCpjChunkHeader[4] > 0:
                    name = ctypes.create_string_buffer(
                        data[idx + SCpjChunkHeader[4]:]).value.decode()
                else:
                    name = "nameless"

                # delegate
                if loop == 0:
                    if magic == CPJ_MAC_MAGIC and version == CPJ_MAC_VERSION:
                        chunk_mac(data, idx, name)

                elif loop == 1:
                    if magic == CPJ_GEO_MAGIC and version == CPJ_GEO_VERSION:
                        if bl_object:
                            print("! multiple GEO blocks are not supported")
                        else:
                            bl_object = chunk_geo(data, idx, name)

                elif loop == 2:
                    if magic == CPJ_SRF_MAGIC and version == CPJ_SRF_VERSION:
                        if has_surface_already:
                            print("! multiple SRF blocks are not supported")
                        elif not bl_object:
                            print("! cannot import SRF without GEO")
                        else:
                            chunk_srf(data, idx, name, bl_object)
                            has_surface_already = True

                else:
                    if magic == CPJ_MAC_MAGIC and version == CPJ_MAC_VERSION:
                        pass
                    elif magic == CPJ_GEO_MAGIC and version == CPJ_GEO_VERSION:
                        pass
                    elif magic == CPJ_SRF_MAGIC and version == CPJ_SRF_VERSION:
                        pass
                    elif magic == CPJ_LOD_MAGIC and version == CPJ_LOD_VERSION:
                        chunk_lod(data, idx, name)
                    elif magic == CPJ_SKL_MAGIC and version == CPJ_SKL_VERSION:
                        chunk_skl(data, idx, name)
                    elif magic == CPJ_FRM_MAGIC and version == CPJ_FRM_VERSION:
                        chunk_frm(data, idx, name)
                    elif magic == CPJ_SEQ_MAGIC and version == CPJ_SEQ_VERSION:
                        chunk_seq(data, idx, name)
                    else:
                        raise ImportError("Unsupported %s v%d chunk" %
                                          (magic, version))

                # seek to next chunk (16 bit aligned)
                idx += SCpjChunkHeader[1] + (SCpjChunkHeader[1] % 2) + 8

    return {'FINISHED'}


# ----------------------------------------------------------------------------
def chunk_mac(data, idx, name):
    print("Cannibal Model Actor Configuration Chunk (MAC)")

    # unsigned long numSections; // number of sections
    # unsigned long ofsSections; // offset of sections in data block
    # unsigned long numCommands; // number of commands
    # unsigned long ofsCommands; // offset of command strings in data block
    SMacFile = struct.unpack_from("IIII", data, idx + 20)

    print("- '%s'" % name)
    print("- %d Sections" % SMacFile[0])
    print("- %d Commands" % SMacFile[2])

    # offset
    block = idx + 20 + 16

    # read sections
    shift = block + SMacFile[1]
    for i in range(SMacFile[0]):

        # unsigned long ofsName // offset of section name string in data block
        # unsigned long numCommands // number of command strings in section
        # unsigned long firstCommand // first command string index
        SMacSection = struct.unpack_from("III", data, shift)

        section = ctypes.create_string_buffer(
            data[block + SMacSection[0]:]).value.decode()

        # read commands
        count = SMacSection[1]
        for j in range(count):

            ofs = struct.unpack_from("I", data,
                                     block + SMacFile[3] + (SMacSection[2] + j) * 4)[0]
            command = ctypes.create_string_buffer(
                data[block + ofs:]).value.decode()

            print("+ #%d %s %d/%d : %s" %
                  (i + 1, section, j + 1, count, command))

        # next section
        shift += 12


# ----------------------------------------------------------------------------
def chunk_geo(data, idx, name):
    print("Geometry Chunk (GEO)")

    # unsigned long numVertices; // number of vertices
    # unsigned long ofsVertices; // offset of vertices in data block
    # unsigned long numEdges; // number of edges
    # unsigned long ofsEdges; // offset of edges in data block
    # unsigned long numTris; // number of triangles
    # unsigned long ofsTris; // offset of triangles in data block
    # unsigned long numMounts; // number of mounts
    # unsigned long ofsMounts; // offset of mounts in data block
    # unsigned long numObjLinks; // number of object links
    # unsigned long ofsObjLinks; // number of object links in data
    SGeoFile = struct.unpack_from("IIIIIIIIII", data, idx + 20)

    print("- '%s'" % name)
    print("- %d Vertices" % SGeoFile[0])
    print("- %d Edges" % SGeoFile[2])
    print("- %d Tris" % SGeoFile[4])
    print("- %d Mounts" % SGeoFile[6])
    print("- %d ObjLinks" % SGeoFile[8])

    cpj_verts = []
    cpj_edges = []
    cpj_tris = []

    # read all vertices
    shift = idx + 20 + 40 + SGeoFile[1]
    for i in range(SGeoFile[0]):

        # unsigned char flags; // GEOVF_ vertex flags
        # unsigned char groupIndex; // group index for vertex frame compression
        # unsigned short reserved; // reserved for future use, must be zero
        # unsigned short numEdgeLinks; // number of edges linked to this vertex
        # unsigned short numTriLinks; // number of triangles linked to this vertex
        # unsigned long firstEdgeLink; // first edge index in object link array
        # unsigned long firstTriLink; // first triangle index in object link array
        # CPJVECTOR refPosition; // reference position of vertex
        SGeoVert = struct.unpack_from("BBHHHIIfff", data, shift)

        cpj_verts.append((SGeoVert[7], SGeoVert[9], SGeoVert[8]))  # X Z Y
        shift += 28

    # read all edges
    shift = idx + 20 + 40 + SGeoFile[3]
    for i in range(SGeoFile[2]):

        # unsigned short headVertex; // vertex list index of edge's head vertex
        # unsigned short tailVertex; // vertex list index of edge's tail vertex
        # unsigned short invertedEdge; // edge list index of inverted mirror edge
        # unsigned short numTriLinks; // number of triangles linked to this edge
        # unsigned long firstTriLink; // first triangle index in object link array
        SGeoEdge = struct.unpack_from("HHHHI", data, shift)

        cpj_edges.append((SGeoEdge[0], SGeoEdge[1]))
        shift += 12

    # read all triangles
    shift = idx + 20 + 40 + SGeoFile[5]
    for i in range(SGeoFile[4]):

        # unsigned short edgeRing[3]; // edge list indices used by triangle, whose
        #                             // tail vertices are V0, V1, and V2, in order
        # unsigned short reserved; // reserved for future use, must be zero
        SGeoTri = struct.unpack_from("HHHH", data, shift)

        cpj_tris.append((SGeoTri[0], SGeoTri[1], SGeoTri[2]))
        shift += 8

    # create list of mesh faces
    bl_faces = []
    for tris in cpj_tris:
        v0 = cpj_edges[tris[0]][1]
        v1 = cpj_edges[tris[1]][1]
        v2 = cpj_edges[tris[2]][1]
        bl_faces.append((v0, v1, v2))

    # create mesh and object
    mesh_data = bpy.data.meshes.new(name)
    mesh_data.from_pydata(cpj_verts, [], bl_faces)
    mesh_data.update()
    obj = bpy.data.objects.new(name, mesh_data)
    scene = bpy.context.scene
    scene.collection.objects.link(obj)

    return obj


# ----------------------------------------------------------------------------
def chunk_srf(data, idx, name, bl_object):
    print("Surface Chunk (SRF)")

    # unsigned long numTextures; // number of textures
    # unsigned long ofsTextures; // offset of textures in data block
    # unsigned long numTris; // number of triangles
    # unsigned long ofsTris; // offset of triangles in data block
    # unsigned long numUV; // number of UV texture coordinates
    # unsigned long ofsUV; // offset of UV texture coordinates in data block
    SSrfFile = struct.unpack_from("IIIIII", data, idx + 20)

    print("- '%s'" % name)
    print("- %d numTextures" % SSrfFile[0])
    print("- %d numTris" % SSrfFile[2])
    print("- %d numUV" % SSrfFile[4])

    # create new empty UV layer
    bl_uv_layer = bl_object.data.uv_layers.new(name=name, do_init=False)

    # init bmesh with object mesh
    bm = bmesh.new()
    bm.from_mesh(bl_object.data)
    bm.faces.ensure_lookup_table()
    uv = bm.loops.layers.uv[0]

    # check consistency
    if SSrfFile[2] != len(bm.faces):
        raise ImportError("Different number of mesh faces in GEO and SRF")

    # offset
    block = idx + 20 + 24

    # read textures
    shift = block + SSrfFile[1]
    for i in range(SSrfFile[0]):

        # unsigned long ofsName; // offset of texture name string in data block
        # unsigned long ofsRefName; // offset of optional reference name in block
        SSrfTex = struct.unpack_from("II", data, shift)

        label = ctypes.create_string_buffer(
            data[block + SSrfTex[0]:]).value.decode()
        if SSrfTex[1]:
            label += "___" + ctypes.create_string_buffer(
                data[block + SSrfTex[1]:]).value.decode()

        # make new texture with random colors
        col = colorsys.hls_to_rgb(random.random(), 0.6, 0.8)
        mat = bpy.data.materials.new(name=label)
        mat.diffuse_color = (col[0], col[1], col[2], 1.0)
        bl_object.data.materials.append(mat)

        shift += 8

    # read triangles
    shift = block + SSrfFile[3]
    for i in range(SSrfFile[2]):

        # unsigned short uvIndex[3]; // UV texture coordinate indices used
        # unsigned char texIndex; // surface texture index
        # unsigned char reserved; // reserved for future use, must be zero
        # unsigned long flags; // SRFTF_ triangle flags
        # unsigned char smoothGroup; // light smoothing group
        # unsigned char alphaLevel; // transparent/modulated alpha level
        # unsigned char glazeTexIndex; // second-pass glaze texture index if used
        # unsigned char glazeFunc; // ESrfGlaze second-pass glaze function
        SSrfTri = struct.unpack_from("HHHBBIBBBB", data, shift)

        # set UVs
        uv0 = struct.unpack_from(
            "ff", data, block + SSrfFile[5] + SSrfTri[0] * 8)
        uv1 = struct.unpack_from(
            "ff", data, block + SSrfFile[5] + SSrfTri[1] * 8)
        uv2 = struct.unpack_from(
            "ff", data, block + SSrfFile[5] + SSrfTri[2] * 8)
        bm.faces[i].loops[0][uv].uv = (uv0[0], 1.0 - uv0[1])
        bm.faces[i].loops[1][uv].uv = (uv1[0], 1.0 - uv1[1])
        bm.faces[i].loops[2][uv].uv = (uv2[0], 1.0 - uv2[1])

        # set material index
        bm.faces[i].material_index = SSrfTri[3]

        # TODO flags
        # SRFTF_INACTIVE    = 0x00000001, // triangle is not active
        # SRFTF_HIDDEN      = 0x00000002, // present but invisible
        # SRFTF_VNIGNORE    = 0x00000004, // ignored in vertex normal calculations
        # SRFTF_TRANSPARENT = 0x00000008, // transparent rendering is enabled
        # SRFTF_UNLIT       = 0x00000020, // not affected by dynamic lighting
        # SRFTF_TWOSIDED    = 0x00000040, // visible from both sides
        # SRFTF_MASKING     = 0x00000080, // color key masking is active
        # SRFTF_MODULATED   = 0x00000100, // modulated rendering is enabled
        # SRFTF_ENVMAP      = 0x00000200, // environment mapped
        # SRFTF_NONCOLLIDE  = 0x00000400, // traceray won't collide with this surface
        # SRFTF_TEXBLEND    = 0x00000800,
        # SRFTF_ZLATER      = 0x00001000,
        # SRFTF_RESERVED    = 0x00010000

        shift += 16

    # update object mesh
    bm.to_mesh(bl_object.data)
    bm.free()


# ----------------------------------------------------------------------------
def chunk_lod(data, idx, name):
    print("Level Of Detail Chunk (LOD)")
    print("- '%s'" % name)
    print("! unsupported")


# ----------------------------------------------------------------------------
def chunk_skl(data, idx, name):
    print("Skeleton Chunk (SKL)")
    print("- '%s'" % name)
    print("! unsupported")


# ----------------------------------------------------------------------------
def chunk_frm(data, idx, name):
    print("Vertex Frames Chunk (FRM)")
    print("- '%s'" % name)
    print("! unsupported")


# ----------------------------------------------------------------------------
def chunk_seq(data, idx, name):
    print("Sequenced Animation Chunk (SEQ)")
    print("- '%s'" % name)
    print("! unsupported")


# EoF
