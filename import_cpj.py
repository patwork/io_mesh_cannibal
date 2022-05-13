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
import bpy


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
            if magic == CPJ_MAC_MAGIC and version == CPJ_MAC_VERSION:
                chunk_mac(data, idx, name)
            elif magic == CPJ_GEO_MAGIC and version == CPJ_GEO_VERSION:
                chunk_geo(data, idx, name)
            else:
                print("Unsupported %s v%d chunk" % (magic, version))

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

        # read comments
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

        cpj_verts.append((SGeoVert[7], SGeoVert[9], SGeoVert[8]))
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

# EoF
