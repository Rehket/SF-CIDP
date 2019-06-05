# SalesForce Continuous Integration and Data Pipeline 

## This project is done mostly for fun and learning, but issues and pull requests are welcome!


## What is the purpose of this tool?
**< Some Amazing Name Here >** aims to make migrating changes and data between salesforce environments simple with integration into VCS. 
 So simple, such that there is no reason to not to use verson control, even if the org is a mess :P.
 
### Tasks That kinda work. i.e. works in some situations.

- *Quick Deploy from Github to SalesForce* - Take the metadata from a git repo, and put it in a SalesForce instance
- *Migrate Metadata from one instance to another* - Take the metadata from a SFDC instance, and migrate it to another.

### Future Features
- *Migrate Metadata through Instance Environments in sync with git* - Take the metadata from a SFDC instance, and migrate it to another.

- *Provide an Service API to trigger build and migration events from SalesForce* - Managing Metadata items and 
migrations for admins who do not want to deal with git.


### Process Flow

-------

![Process Flow](/docs/SF_CICD.png)
