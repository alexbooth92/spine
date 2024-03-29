"""Module that contains all parsers related to LArCV particle data.

Contains the following parsers:
- :class:`ParticleParser`
- :class:`NeutrinoParser`
- :class:`ParticlePointParser`
- :class:`ParticleCoordinateParser`
- :class:`ParticleGraphParser`
- :class:`ParticlePIDParser`
- :class:`ParticleEnergyParser`
"""

import numpy as np
from larcv import larcv

from mlreco.utils.globals import TRACK_SHP, PDG_TO_PID, PID_MASSES
from mlreco.utils.data_structures import Meta, Particle, Neutrino, ObjectList
from mlreco.utils.particles import process_particles
from mlreco.utils.ppn import get_ppn_labels

from .parser import Parser

__all__ = ['ParticleParser', 'NeutrinoParser', 'ParticlePointParser',
           'ParticleCoordinateParser', 'ParticleGraphParser',
           'SingleParticlePIDParser', 'SingleParticleEnergyParser']


class ParticleParser(Parser):
    """Class which loads larcv.Particle objects to local Particle ones.

    .. code-block. yaml

        schema:
          particles:
            parser: parse_particles
            particle_event: particle_pcluster
            cluster_event: cluster3d_pcluster
            pixel_coordinates: True
    """
    name = 'parse_particles'

    def __init__(self, pixel_coordinates=True, post_process=True, **kwargs):
        """Initialize the parser.

        Parameters
        ----------
        pixel_coordinates : bool, default True
            If set to `True`, the parser rescales the truth positions
            (start, end, etc.) to voxel coordinates
        post_process : bool, default True
            Processes particles to add/correct missing attributes
        **kwargs : dict, optional
            Data product arguments to be passed to the `process` function
        """
        # Initialize the parent class
        super().__init__(**kwargs)

        # Store the revelant attributes
        self.pixel_coordinates = pixel_coordinates
        self.post_process = post_process

    def process(self, particle_event, sparse_event=None, cluster_event=None,
                particle_mpv_event=None, neutrino_event=None):
        """Fetch the list of true particle objects.

        Parameters
        ----------
        particle_event : larcv.EventParticle
            Particle event which contains the list of true particles
        sparse_event : larcv.EventSparseTensor3D, optional
            Tensor which contains the metadata needed to convert the
            positions in voxel coordinates
        cluster_event : larcv.EventClusterVoxel3D, optional
            Cluster which contains the metadata needed to convert the
            positions in voxel coordinates
        particle_mpv_event : larcv.EventParticle, optional
            Particle event which contains the list of true MPV particles
        neutrino_event : larcv.EventNeutrino, optional
            Neutrino event which contains the list of true neutrinos

        Returns
        -------
        List[Particle]
            List of true particle objects
        """
        # Convert to a list of particle objects
        particle_list = particle_event.as_vector()
        particles = [Particle.from_larcv(p) for p in particle_list]

        # If requested, post-process the particle list
        if self.post_process:
            # Fetch the secondary information
            particles_mpv, neutrinos = None, None
            if particle_mpv_event is not None:
                particle_mpv_list = particle_mpv_event.as_vector()
                particles = [Particle.from_larcv(p) for p in particle_mpv_list]
            if neutrino_event is not None:
                neutrino_list = neutrino_event.as_vector()
                neutrinos = [Neutrino.from_larcv(n) for n in neutrino_list]

            process_particles(particles, particles_mpv, neutrinos)

        # If requested, convert the point positions to pixel coordinates
        if self.pixel_coordinates:
            # Fetch the metadata
            assert (sparse_event is not None) ^ (cluster_event is not None), (
                    "Must provide either `sparse_event` or `cluster_event` to "
                    "get the metadata and convert positions to voxel units.")
            ref_event = sparse_event if sparse_event else cluster_event
            meta = Meta.from_larcv(ref_event.meta())

            # Convert all the relevant attributes
            for p in particles:
                p.to_pixel(meta)

        return ObjectList(particles, Particle())


class NeutrinoParser(Parser):
    """Class which loads larcv.Neutrino objects to local Neutrino ones.

    .. code-block. yaml

        schema:
          neutrinos:
            parser: parse_neutrinos
            neutrino_event: neutrino_mpv
            cluster_event: cluster3d_pcluster
            pixel_coordinates: True
    """
    name = 'parse_neutrinos'

    def __init__(self, pixel_coordinates=True, **kwargs):
        """Initialize the parser.

        Parameters
        ----------
        pixel_coordinates : bool, default True
            If set to `True`, the parser rescales the truth positions
            (start, end, etc.) to voxel coordinates
        **kwargs : dict, optional
            Data product arguments to be passed to the `process` function
        """
        # Initialize the parent class
        super().__init__(**kwargs)

        # Store the revelant attributes
        self.pixel_coordinates = pixel_coordinates

    def process(self, neutrino_event, sparse_event=None, cluster_event=None):
        """Fetch the list of true neutrino objects.

        Parameters
        ----------
        neutrino_event : larcv.EventNeutrino
            Neutrino event which contains the list of true neutrinos
        sparse_event : larcv.EventSparseTensor3D, optional
            Tensor which contains the metadata needed to convert the
            positions in voxel coordinates
        cluster_event : larcv.EventClusterVoxel3D, optional
            Cluster which contains the metadata needed to convert the
            positions in voxel coordinates

        Returns
        -------
        List[Neutrino]
            List of true neutrino objects
        """
        # Convert to a list of neutrino objects
        neutrino_list = neutrino_event.as_vector()
        neutrinos = [Neutrino.from_larcv(n) for n in neutrino_list]

        # If requested, convert the point positions to pixel coordinates
        if self.pixel_coordinates:
            # Fetch the metadata
            assert (sparse_event is not None) ^ (cluster_event is not None), (
                    "Must provide either `sparse_event` or `cluster_event` to "
                    "get the metadata and convert positions to voxel units.")
            ref_event = sparse_event if sparse_event else cluster_event
            meta = Meta.from_larcv(ref_event.meta())

            # Convert all the relevant attributes
            for n in neutrinos:
                n.to_pixel(meta)

        return ObjectList(neutrinos, Neutrino())


class ParticlePointParser(Parser):
    """Class that retrieves the points of interests.

    It provides the coordinates of the end points, types and particle index.

    .. code-block. yaml

        schema:
          points:
            parser: parse_particle_points
            particle_event: particle_pcluster
            sparse_event: sparse3d_pcluster
            include_point_tagging: True
    """
    name = 'parse_particle_points'

    def __init__(self, include_point_tagging=True, **kwargs):
        """Initialize the parser.

        Parameters
        ----------
        include_point_tagging : bool, default True
            If `True`, includes start vs end point tagging
        **kwargs : dict, optional
            Data product arguments to be passed to the `process` function
        """
        # Initialize the parent class
        super().__init__(**kwargs)

        # Store the revelant attributes
        self.include_point_tagging = include_point_tagging

    def process(self, particle_event, sparse_event=None, cluster_event=None):
        """Fetch the list of label points of interest.

        Parameters
        ----------
        particle_event : larcv.EventParticle
            Particle event which contains the list of true particles
        sparse_event : larcv.EventSparseTensor3D, optional
            Tensor which contains the metadata needed to convert the
            positions in voxel coordinates
        cluster_event : larcv.EventClusterVoxel3D, optional
            Cluster which contains the metadata needed to convert the
            positions in voxel coordinates
            
        Returns
        -------
        np_voxels : np.ndarray
            (N, 3) array of [x, y, z] coordinates
        np_features : np.ndarray
            (N, 2/3) array of [point type, particle index(, end point tagging)]
        meta : Meta
            Metadata of the parsed image
        """
        # Fetch the metadata
        assert (sparse_event is not None) ^ (cluster_event is not None), (
                "Must provide either `sparse_event` or `cluster_event` to "
                "get the metadata and convert positions to voxel units.")
        ref_event = sparse_event if sparse_event else cluster_event
        meta = ref_event.meta()

        # Get the point labels
        particles_v = particle_event.as_vector()
        point_labels = get_ppn_labels(
                particles_v, meta,
                include_point_tagging=self.include_point_tagging)

        return point_labels[:, :3], point_labels[:, 3:], Meta.from_larcv(meta)


class ParticleCoordinateParser(Parser):
    """Class that retrieves that end points of particles.

    It provides the coordinates of the end points, time and shape.

    .. code-block. yaml

        schema:
          coords:
            parser: parse_particle_coordinates
            particle_event: particle_pcluster
            sparse_event: sparse3d_pcluster
    """
    name = 'parse_particle_coords'

    def __init__(self, pixel_coordinates=True, **kwargs):
        """Initialize the parser.

        Parameters
        ----------
        pixel_coordinates : bool, default True
            If set to `True`, the parser rescales the truth positions
            (start, end, etc.) of the particle information to voxel coordinates
        **kwargs : dict, optional
            Data product arguments to be passed to the `process` function
        """
        # Initialize the parent class
        super().__init__(**kwargs)

        # Initialize the particle parser
        self.particle_parser = ParticleParser(
                pixel_coordinates=pixel_coordinates, post_process=False)

    def process(self, particle_event, sparse_event=None, cluster_event=None):
        """Fetch the start/end point and time of each true particle.

        Parameters
        ----------
        particle_event : larcv.EventParticle
            Particle event which contains the list of true particles
        sparse_event : larcv.EventSparseTensor3D, optional
            Tensor which contains the metadata needed to convert the
            positions in voxel coordinates
        cluster_event : larcv.EventClusterVoxel3D, optional
            Cluster which contains the metadata needed to convert the
            positions in voxel coordinates
            
        Returns
        -------
        np_voxels : np.ndarray
            (N, 3) array of [x, y, z] start point coordinates
        np_features : np.ndarray
            (N, 8) array of [first_step_x, first_step_y, first_step_z,
            last_step_x, last_step_y, last_step_z, first_step_t, shape_id]
        meta : Meta
            Metadata of the parsed image
        """
        # Fetch the metadata
        assert (sparse_event is not None) ^ (cluster_event is not None), (
                "Must provide either `sparse_event` or `cluster_event` to "
                "get the metadata and convert positions to voxel units.")
        ref_event = sparse_event if sparse_event else cluster_event
        meta = ref_event.meta()

        # Scale particle coordinates to image size
        particles = self.particle_parser.process(particle_event, ref_event)

        # Make features
        features = []
        for i, p in enumerate(particles):
            start_point = last_point = p.first_step
            if p.shape == TRACK_SHP: # End point only meaningful for tracks
                last_point = p.last_step
            extra = [p.t, p.shape]
            features.append(np.concatenate((start_point, last_point, extra)))

        features = np.vstack(features)

        return features[:, :6], features[:, 6:], Meta.from_larcv(meta)


class ParticleGraphParser(Parser):
    """Class that uses larcv.EventParticle to construct edges
    between particles (i.e. clusters).

    .. code-block. yaml

        schema:
          graph:
            parser: parse_particle_graph
            particle_event: particle_pcluster
            cluster_event: cluster3d_pcluster

    """
    name = 'parse_particle_graph'

    def process(self, particle_event, cluster_event=None):
        """Fetch the parentage connections from the true particle list.

        Configuration
        -------------
        particle_event : larcv.EventParticle
            Particle event which contains the list of true particles
        cluster_event : larcv.EventClusterVoxel3D, optional
            Cluster used to check if particles have 0 pixel in the image. If
            so, the edges to those clusters are removed and the broken
            parantage is subsequently patched.

        Returns
        -------
        np.ndarray
            (2, E) Array of directed edges for each [parent, child] connection
        int
            Number of particles in the input
        """
        particles_v   = particle_event.as_vector()
        num_particles = particles_v.size()
        edges         = []
        if cluster_event is None:
            # Fill edges (directed [parent, child] pair)
            edges = []
            for cluster_id in range(num_particles):
                p = particles_v[cluster_id]
                if p.parent_id() != p.id():
                    edges.append([int(p.parent_id()), cluster_id])
                if p.parent_id() == p.id() and p.group_id() != p.id():
                    edges.append([int(p.group_id()), cluster_id])

            # Convert the list of edges to a numpy array
            if not len(edges):
                return np.empty((0, 2), dtype=np.int32), num_particles

            edges = np.vstack(edges).astype(np.int32)

        else:
            # Check that the cluster and particle objects are consistent
            num_clusters = cluster_event.size()
            assert (num_particles == num_clusters or
                    num_particles == num_clusters - 1), (
                    f"The number of particles ({num_particles}) must be "
                    f"aligned with the number of clusters ({num_clusters}). "
                    f"There can me one more catch-all cluster at the end.")

            # Fill edges (directed [parent, child] pair)
            zero_nodes, zero_nodes_pid = [], []
            for cluster_id in range(num_particles):
                cluster = cluster_event.as_vector()[cluster_id]
                num_points = cluster.as_vector().size()
                p = particles_v[cluster_id]
                if p.id() != p.group_id():
                    continue
                if p.parent_id() != p.group_id():
                    edges.append([int(p.parent_id()), p.group_id()])
                if num_points == 0:
                    zero_nodes.append(p.group_id())
                    zero_nodes_pid.append(cluster_id)

            # Convert the list of edges to a numpy array
            if not len(edges):
                return np.empty((0, 2), dtype=np.int32), num_particles

            edges = np.vstack(edges).astype(np.int32)

            # Remove zero pixel nodes
            for i, zn in enumerate(zero_nodes):
                children = np.where(edges[:, 0] == zn)[0]
                if len(children) == 0:
                    edges = edges[edges[:, 0] != zn]
                    edges = edges[edges[:, 1] != zn]
                    continue
                parent = np.where(edges[:, 1] == zn)[0]
                assert len(parent) <= 1

                # If zero node has a parent, then assign children to that parent
                if len(parent) == 1:
                    parent_id = edges[parent][0][0]
                    edges[:, 0][children] = parent_id
                else:
                    edges = edges[edges[:, 0] != zn]
                edges = edges[edges[:, 1] != zn]

        return edges.T, num_particles


class SingleParticlePIDParser(Parser):
    """Get the first true particle's species.

    .. code-block. yaml

        schema:
          pdg_list:
            parser: parse_single_particle_pdg
            particle_event: particle_pcluster
    """
    name = 'parse_single_particle_pdg'
    aliases = ['parse_particle_singlep_pdg']

    def process(self, particle_event):
        """Fetch the species of the first particle.

        Configuration
        -------------
        particle_event : larcv.EventParticle
            Particle event which contains the list of true particles

        Returns
        -------
        int
            Species of the first particle
        """
        pdg = -1
        for p in particle_event.as_vector():
            if p.track_id() == 1:
                if int(p.pdg_code()) in PDG_TO_PID.keys():
                    pdg = PDG_TO_PID[int(p.pdg_code())]

                break

        return pdg


class SingleParticleEnergyParser(Parser):
    """Get the first true particle's kinetic energy.

    .. code-block. yaml

        schema:
          energy_list:
            parser: parse_single_particle_energy
            particle_event: particle_pcluster
    """
    name = 'parse_single_particle_energy'
    aliases = ['parse_particle_singlep_enit']

    def process(self, particle_event):
        """Fetch the kinetic energy of the first particle.

        Configuration
        -------------
        particle_event : larcv.EventParticle
            Particle event which contains the list of true particles

        Returns
        -------
        float
            Kinetic energy of the first particle
        """
        ke = -1.
        for p in particle_event.as_vector():
            if p.track_id() == 1:
                if int(p.pdg_code()) in PDG_TO_PID.keys():
                    einit = p.energy_init()
                    pid = PDG_TO_PID[int(p.pdg_code())]
                    mass = PID_MASSES[pid]
                    ke = einit - mass

                break

        return ke
