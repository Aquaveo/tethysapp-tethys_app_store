===============
Getting Started
===============

This application can be installed on your local Tethys portal in the following ways: 

Install using Miniconda (Recommended)
*************************************

While using Miniconda install, we need to ensure that the Tethys portal is setup to allow for communication over websockets by setting up an in-memory channel layer:

.. code-block:: shell

	# If you haven't set this already
	tethys settings --set CHANNEL_LAYERS.default.BACKEND channels.layers.InMemoryChannelLayer


Following that, installing the app store is a simple conda install command: 

.. code-block:: shell

	conda install -c tethysapp app_store



Install from GitHub
********************

.. code-block:: shell

	# Activate tethys environment if not already active
	conda activate tethys

	git clone https://github.com/BYU-Hydroinformatics/tethysapp-tethys_app_store.git
	cd tethysapp-tethys_app_store
	tethys install



Updating Installed App Store
****************************

If you installed the app store using the Miniconda command, then run the following command to update the app store to the latest version: 

.. code-block:: shell

	# Activate Tethys environment if not already active
	conda activate tethys

	conda install -c tethysapp app_store

In case you installed the app store from GitHub, just pull the latest changes: 

.. code-block:: shell

	cd <directory_where_app_store_is_installed>
	git pull



Configuring App Store Settings
******************************

After the app store has been installed in tethys, you will need to configure the following settings.

**sudo_server_pass (optional)**: This is the sudo password for the server running the tethys portal. This is used to help 
restart the tethys portal after new applications are installed. Other methods are used first to restart the server so
this may not be needed.

**encryption_key (required)**: This is the encryption key used to created the encrypted tokens in the store settings. In order 
to create encrypted keys and tokens, do the following:

.. code-block:: python

	>>> from cryptography.fernet import Fernet
	>>> encryption_key = Fernet.generate_key()
	>>> f = Fernet(encryption_key)
	>>> encrypted_github_token = f.encrypt(b"my_github_token")

**stores_settings (required)**: The app store requires a github organization and a conda channel in order to submit and 
install applications. This json has to following pattern:

.. code-block:: json

	{
		"stores": [
			{
			"default": "<true|false>",
			"github_organization": "FIRO-Tethys",
			"github_token": "<encrypted github token for repo access, creating repos, updating repos, etc>",
			"conda_channel": "<conda channel to use for retrieving and downloading apps>",
			"conda_labels": "<comma delimited string for conda labels to be used>"
			}
		]
	}

An example of the stores_settings would be:

.. code-block:: json

	{
		"stores": [
			{
			"default": true,
			"conda_labels": "main",
			"github_token": "abcdefg12345678",
			"conda_channel": "tethysapp",
			"github_organization": "tethysapp"
			}
		]
	}


Migrating from Warehouse to App Store
*************************************

In September, 2021 this package went through a name change and all future updates are published as `app-store` and not `warehouse`. If you have an existing version of the `Tethys App Warehouse` installed on your system, please follow the following steps to update it to the `Tethys App Store`. These steps assume you had installed the warehouse using Miniconda. 

For GitHub installs, please follow the standard uninstall and install new app procedures. 

.. code-block:: shell

	# Activate Tethys environment if not already active
	conda activate tethys

	tethys uninstall warehouse

	conda remove -c tethysplatform --override-channels warehouse

	conda install -c tethysapp app_store

	# Restart your Tethys Instance (If Running in production)

	sudo supervisorctl restart all







