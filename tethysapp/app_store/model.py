from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, Boolean, ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.exc import IntegrityError

from .app import AppStore as app

Base = declarative_base()


class Application(Base):
    """
    SQLAlchemy Applicatons DB Model
    """
    __tablename__ = 'applications'

    # Columns
    id = Column(Integer, primary_key=True)
    app_name = Column(String)
    conda_channel = Column(String)
    app_type = Column(String)

    versions = relationship("Version", back_populates='app')
    __table_args__ = (UniqueConstraint('app_name', 'conda_channel', name="app_constraint"),)


class Version(Base):
    """
    SQLAlchemy Versions DB Model
    """
    __tablename__ = 'versions'

    # Columns
    id = Column(Integer, primary_key=True) 
    app_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    conda_label = Column(String)
    app_version = Column(Float)
    app_version_url = Column(String)
    compatibility = Column(String)
    author = Column(String)
    author_email = Column(String)
    description = Column(String)
    installed = Column(Boolean)
    app = relationship("Application", back_populates='versions')
    keywords = relationship("Keyword", secondary="keywords_link", back_populates='app_version')

    __table_args__ = (UniqueConstraint('app_id', 'conda_label', 'app_version', name="app_version_constraint"),)


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
        add_new_application("test_application", "conda_channel", "tethysapp")
        add_new_application("test_application2", "conda_channel", "tethysapp2")
    else:
        breakpoint()
        Session = app.get_persistent_store_database('primary_db', as_sessionmaker=True)
        session = Session()
        installed_versions = session.query(Version).where(Version.installed==True).all()
        


def add_new_application(app_name, conda_channel, app_type):
    
    new_app = Application(
        app_name=app_name,
        conda_channel=conda_channel,
        app_type=app_type
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
    
    versions = [
        {
            "conda_label": "main",
            "app_version": 1.8,
            "app_version_url": None,
            "compatibility": None,
            "author": None,
            "author_email": None,
            "description": "This is a test app",
            "installed": True,
            "keywords": ["tethysapp", "test",]
        },
        {
            "conda_label": "main",
            "app_version": 1.9,
            "app_version_url": None,
            "compatibility": None,
            "author": None,
            "author_email": None,
            "description": "This is a test app",
            "installed": True,
            "keywords": ["tethysapp", "test2"]
        }
    ]
    
    for version in versions:
        new_version = Version(
            app_id=new_app.id,
            conda_label=version["conda_label"],
            app_version=version["app_version"],
            app_version_url=version["app_version_url"],
            compatibility=version["compatibility"],
            author=version["author"],
            author_email=version["author_email"],
            description=version["description"],
            installed=version["installed"]
        )
    
        session.add(new_version)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            print(f"Version {version["app_version"]} for {app_name}(id {new_app.id}) with the {version["conda_label"]} label already exists")

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
    