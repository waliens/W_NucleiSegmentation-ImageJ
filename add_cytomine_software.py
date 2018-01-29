import cytomine
import sys

#Connect to cytomine, edit connection values

cytomine_host="my-host"  # Cytomine core URL
cytomine_public_key="my-public-key"  # Your public key
cytomine_private_key="my-private-key" # Your private key
id_project=my-project-id
 
#Connection to Cytomine Core
conn = cytomine.Cytomine(cytomine_host, cytomine_public_key, cytomine_private_key, base_path = '/api/', working_path = '/tmp/', verbose= True)
 
execute_command = "python algo/ij_segment_clustered_nuclei/wrapper.py --ij_radius $ij_radius --ij_threshold $ij_threshold " + "--cytomine_host $host " + "--cytomine_public_key $publicKey " +"--cytomine_private_key $privateKey " + "--cytomine_id_project $cytomine_id_project "

#define software parameter template
software = conn.add_software("IJSegmentClusteredNuclei", "createRabbitJobWithArgsService","ValidateAnnotation", execute_command)
conn.add_software_parameter("ij_radius", software.id, "Number", 5, True, 10, False)
conn.add_software_parameter("ij_threshold", software.id, "Number", -0.5, True, 30, False)
 
#for logging (set by server)
conn.add_software_parameter("cytomine_id_software", software.id, "Number",0, True, 400, True)
conn.add_software_parameter("cytomine_id_project", software.id, "Number", 0, True, 500, True)

#add software to a given project
addSoftwareProject = conn.add_software_project(id_project,software.id)
