from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, Boolean, ForeignKey, UniqueConstraint, desc, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError
from conda.cli.python_api import run_command as conda_run, Commands
import os
import json
import shutil
import urllib
import yaml

from tethys_sdk.workspaces import get_app_workspace

from .app import AppStore as app
from .helpers import get_conda_stores, logger
from .utilities import update_version

Base = declarative_base()


class Application(Base):
    """
    SQLAlchemy Applicatons DB Model
    """
    __tablename__ = 'applications'

    # Columns
    id = Column(Integer, primary_key=True)
    app_name = Column(String)
    app_type = Column(String)
    conda_channel = Column(String)
    conda_label = Column(String)

    versions = relationship("Version", back_populates='app', order_by="Version.app_version_major.desc(), Version.app_version_minor.desc(), Version.app_version_patch.desc()")
    __table_args__ = (UniqueConstraint('app_name', 'conda_channel', 'conda_label', name="app_constraint"),)


class Version(Base):
    """
    SQLAlchemy Versions DB Model
    """
    __tablename__ = 'versions'

    # Columns
    id = Column(Integer, primary_key=True) 
    app_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    app_version = Column(String)
    app_version_major = Column(Integer)
    app_version_minor = Column(Integer)
    app_version_patch = Column(Integer)
    app_version_url = Column(String)
    compatibility = Column(String)
    author = Column(String)
    author_email = Column(String)
    description = Column(String)
    installed = Column(Boolean)
    app = relationship("Application", back_populates='versions')
    keywords = relationship("Keyword", secondary="keywords_link", back_populates='app_version')

    __table_args__ = (UniqueConstraint('app_id', 'app_version', name="app_version_constraint"),)


class Keyword(Base):
    """
    SQLAlchemy Keywords DB Model
    """
    __tablename__ = 'keywords'

    # Columns
    id = Column(Integer, primary_key=True) 
    keyword = Column(String, unique=True)
    app_version = relationship("Version", secondary="keywords_link", back_populates='keywords')


class KeywordsLink(Base):
    """
    SQLAlchemy Keywords Linking DB Model
    """
    __tablename__ = 'keywords_link'

    # Columns
    id = Column(Integer, primary_key=True) 
    keyword_id = Column(Integer, ForeignKey("keywords.id"), nullable=False)
    app_version_id = Column(Integer, ForeignKey("versions.id"), nullable=False)


def init_primary_db(engine, first_time):
    """
    Initializer for the primary database.
    """
    # Create all the tables
    Base.metadata.create_all(engine)

    # Add data
    if first_time:
        app_workspace = get_app_workspace(app)
        available_stores = get_conda_stores()
        for store in available_stores:
            conda_channel = store['conda_channel']
            for conda_label in store['conda_labels']:
                upload_conda_applications_to_db(app_workspace, conda_channel, conda_label)


def upload_conda_applications_to_db(app_workspace, conda_channel, conda_label):
    conda_search_channel = conda_channel
    if conda_label != 'main':
        conda_search_channel = f'{conda_channel}/label/{conda_label}'

    # Look for packages:
    logger.info(f"Retrieving applications from {conda_search_channel}")
    [resp, err, code] = conda_run(Commands.SEARCH,
                                    ["-c", conda_search_channel, "--override-channels", "-i", "--json"])

    if code != 0:
        # In here maybe we just try re running the install
        raise Exception(f"ERROR: Couldn't search packages in the {conda_search_channel} channel")

    conda_search_result = json.loads(resp)

    resource_metadata = {}
    logger.info("Total Apps Found:" + str(len(conda_search_result)))
    if 'The following packages are not available from current channels' in conda_search_result.get('error', ""):
        logger.info(f'no packages found with the label {conda_label} in channel {conda_channel}')
        return resource_metadata

    for app_name in conda_search_result:
        app_versions = []
        logger.info(f"Getting information for {app_name}")
            
        for conda_version in conda_search_result[app_name]:
            version = conda_version.get('version')
            semver_version = update_version(version)[0]
            version_url = conda_version.get('url')
            license_data = conda_version.get('license')
            
            try:
                license_json = json.loads(license_data.replace("\'", "\""))
                app_version_metadata = get_license_metadata(license_json)
            except:
                app_version_metadata = get_meta_yaml_metadata(
                    app_name, app_workspace, conda_channel, conda_label, version, version_url
                )
            
            app_type = app_version_metadata['app_type']
            app_versions.append({
                "compatibility": app_version_metadata['compatibility'],
                "author": app_version_metadata['author'],
                "author_email": app_version_metadata['author_email'],
                "description": app_version_metadata['description'],
                "keywords": app_version_metadata['keywords'] if app_version_metadata['keywords'] else [],
                "dev_url": app_version_metadata['dev_url'],
                "app_version": version,
                "app_version_major": semver_version.major,
                "app_version_minor": semver_version.minor,
                "app_version_patch": semver_version.patch,
                "app_version_url": version_url
            })
        
        add_new_application_to_db(app_name, conda_channel, conda_label, app_type, app_versions)


def get_license_metadata(license_json):
    app_type = license_json.get('app_type', 'tethysapp')
    if 'tethys_version' in license_json:
        compatibility = license_json.get('tethys_version', '<=3.4.4')

    author = license_json.get("author")
    author_email = license_json.get("author_email")
    description = license_json.get("description")
    license = license_json.get("license")
    dev_url = license_json.get("url")
    keywords = license_json.get("keywords", [])
    if isinstance(keywords, str):
        keywords = keywords.split(",")

    return_object = {
        "app_type": app_type,
        "compatibility": compatibility,
        "author": author,
        "author_email": author_email,
        "description": description,
        "license": license,
        "keywords": keywords,
        "dev_url": dev_url
    }
    
    return return_object


def get_meta_yaml_metadata(app_name, app_workspace, conda_channel, conda_label, version, version_url):
    workspace_folder = os.path.join(app_workspace.path, 'apps')
    if not os.path.exists(workspace_folder):
        os.makedirs(workspace_folder)

    # defaults
    app_type = "tethysapp"
    compatibility = '<=3.4.4'
    author = None
    author_email = None
    description = None
    license = None
    keywords = []
    dev_url = None
        
    # There wasn't json found in license. Get Metadata from downloading the file
    conda_label_path = os.path.join(workspace_folder, conda_channel, conda_label)
    app_path = os.path.join(conda_label_path, app_name)
    app_version_path = os.path.join(app_path, version)
    download_path = os.path.join(app_path, version_url.split('/')[-1])
    
    if not os.path.exists(app_version_path):
        if not os.path.exists(conda_label_path):
            os.makedirs(conda_label_path)
            
        if not os.path.exists(app_path):
            os.makedirs(app_path)

        logger.info(f"License field metadata not found. Downloading {app_name} for version {version}")
        urllib.request.urlretrieve(version_url, download_path)

        shutil.unpack_archive(download_path, app_version_path)
        os.remove(download_path)

    # Get Meta.Yaml for this file
    try:
        meta_yaml_path = os.path.join(app_version_path, 'info', 'recipe', 'meta.yaml')
        if os.path.exists(meta_yaml_path):
            with open(meta_yaml_path) as f:
                meta_yaml = yaml.safe_load(f)
                # Add metadata to the resources object.
                meta_extra = meta_yaml.get("extra", {})
                app_type = meta_extra.get('app_type', 'tethysapp')
                compatibility = meta_extra.get('tethys_version', '<=3.4.4')
                author_email = meta_extra.get("author_email")
                dev_url = meta_extra.get("url")
                keywords = meta_extra.get("keywords", [])
                if isinstance(keywords, str):
                    keywords = keywords.split(",")

                meta_about = meta_yaml.get("about", {})
                author = meta_about.get("author")
                description = meta_about.get("description")
                license = meta_about.get("license")
        else:
            logger.info("No yaml file available to retrieve metadata")
    except Exception as e:
        logger.info("Error happened while downloading package for metadata")
        logger.error(e)

    if os.path.exists(app_version_path):
        shutil.rmtree(app_version_path)
    
    return_object = {
        "app_type": app_type,
        "compatibility": compatibility,
        "author": author,
        "author_email": author_email,
        "description": description,
        "license": license,
        "keywords": keywords,
        "dev_url": dev_url
    }
    
    return return_object
        

def add_new_application_to_db(app_name, conda_channel, conda_label, app_type, app_versions):
    logger.info(f"Adding {app_name} and its associated versions to the DB")
    new_app = Application(
        app_name=app_name,
        app_type=app_type,
        conda_channel=conda_channel,
        conda_label=conda_label
    )

    # Get connection/session to database
    Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
    session = Session()

    # Add the new application record to the session
    session.add(new_app)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        print(f"{app_name} from {conda_channel} already exists")
    
    for version in app_versions:
        new_version = Version(
            app_id=new_app.id,
            app_version=version["app_version"],
            app_version_major=version["app_version_major"],
            app_version_minor=version["app_version_minor"],
            app_version_patch=version["app_version_patch"],
            app_version_url=version["app_version_url"],
            compatibility=version["compatibility"],
            author=version["author"],
            author_email=version["author_email"],
            description=version["description"],
            installed=False
        )
    
        session.add(new_version)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            print(f"Version {version["app_version"]} for {app_name}(id {new_app.id}) with the {conda_label} label already exists")

        for keyword in version["keywords"]:
            new_keyword = Keyword(
                keyword=keyword
            )
            session.add(new_keyword)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                print(f"keyword {keyword} already exists")
    
            new_keyword = KeywordsLink(
                keyword_id=new_keyword.id,
                app_version_id=new_version.id
            )
            session.add(new_keyword)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                print(f"keyword {keyword} already exists")

    # Commit the session and close the connection
    session.close()


def get_available_apps():
    Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
    session = Session()
    
    row_number_column = func.row_number().over(partition_by=Application.id, order_by=(Version.app_version_major.desc(),Version.app_version_minor.desc(),Version.app_version_patch.desc())).label("row_number")
    latest_version_subquery = session.query(
        Application.id,
        Application.app_name,
        Application.app_type,
        Application.conda_channel,
        Application.conda_label,
        Version.app_version,
        Version.installed,
        Version.compatibility,
        row_number_column
    ).join(Application).subquery()

    app_versions_agg = func.array_agg(Version.app_version).label('app_versions')
    all_versions_subquery = session.query(
        Version.app_id,
        app_versions_agg
    ).group_by(Version.app_id).subquery()
    
    available_apps = session.query(
        latest_version_subquery,
        all_versions_subquery.c.app_versions
    ).join(
        all_versions_subquery, all_versions_subquery.c.app_id == latest_version_subquery.c.id
    ).filter(latest_version_subquery.c.row_number == 1).all()

    available_apps_list = []
    for application in available_apps:
        app_dict = {
            "name": application[1],
            "app_type": application[2],
            "conda_channel": application[3],
            "conda_label": application[4],
            "latestVersion": application[5],
            "installed": application[6],
            "compatibility": application[7],
            "versions": application[9],
        }
        available_apps_list.append(app_dict)
    
    return available_apps_list
