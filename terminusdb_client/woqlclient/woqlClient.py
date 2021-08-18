"""woqlClient.py
WOQLClient is the Python public API for TerminusDB"""
import copy
import json
import warnings
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import requests

from ..__version__ import __version__
from ..errors import InterfaceError
from ..woql_utils import _finish_reponse, _result2stream
from ..woqlquery.woql_query import WOQLQuery

# WOQL client object
# license Apache Version 2
# summary Python module for accessing the Terminus DB API


class JWTAuth(requests.auth.AuthBase):
    """Class for JWT Authentication in requests"""

    def __init__(self, token):
        self._token = token

    def __call__(self, r):
        r.headers["Authorization"] = f"Bearer {self._token}"
        return r


class WOQLClient:
    """Client for querying a TerminusDB server using WOQL queries.

    Attributes
    ----------
    server_url: str
        URL of the server that this client connected.
    api: str
        API endpoint for this client.
    account: str
        TerminiusDB account that this client is using. "admin" for local dbs.
    db: str
        Database that this client is connected to.
    user: str
        TerminiusDB user that this client is using. "admin" for local dbs.
    branch: str
        Branch of the database that this client is connected to. Default to "main".
    ref: str, None
        Ref setting for the client. Default to None.
    repo: str
        Repo identifier of the database that this client is connected to. Default to "local".
    """

    def __init__(self, server_url: str, **kwargs) -> None:
        r"""The WOQLClient constructor.

        Parameters
        ----------
        server_url : str
            URL of the server that this client will connect to.
        \**kwargs
            Extra configuration options

        """
        self.server_url = server_url.strip("/")
        self.api = f"{self.server_url}/api"
        self._connected = False

    def connect(
        self,
        account: str = "admin",
        db: Optional[str] = None,
        remote_auth: str = None,
        jwt_token: str = None,
        key: str = "root",
        user: str = "admin",
        branch: str = "main",
        ref: Optional[str] = None,
        repo: str = "local",
        **kwargs,
    ) -> None:
        r"""Connect to a Terminus server at the given URI with an API key.

        Stores the connection settings and necessary meta-data for the connected server. You need to connect before most database operations.

        Parameters
        ----------
        account: str
            Name of the organization account, default to be "admin"
        db: optional, str
            Name of the database connected
        remote_auth: optional, str
            Remote Auth setting
        key: optional, str
            API key for connecting, default to be "root"
        user: optional, str
            Name of the user, default to be "admin"
        branch: optional, str
            Branch to be connected, default to be "main"
        ref: optional, str
            Ref setting
        repo: optional, str
            Local or remote repo, default to be "local"
        \**kwargs
            Extra configuration options.

        Examples
        -------
        >>> client = WOQLClient("https://127.0.0.1:6363")
        >>> client.connect(key="root", account="admin", user="admin", db="example_db")
        """

        self.account = account
        self.db = db
        self._remote_auth = remote_auth
        self._key = key
        self.user = user
        self._jwt_token = jwt_token
        self.branch = branch
        self.ref = ref
        self.repo = repo

        self._connected = True

        try:
            self._all_avaliable_db = json.loads(
                _finish_reponse(requests.get(self.api, auth=self._auth()))
            )
        except Exception:
            raise InterfaceError(
                f"Cannot connect to server, please make sure TerminusDB is running at {self.server_url} and the authentication details are correct."
            ) from None

        all_db_name = list(map(lambda x: x.get("name"), self._all_avaliable_db))
        if self.db is not None and self.db not in all_db_name:
            raise InterfaceError(f"Connection fail, {self.db} does not exist.")

        self._author = self.user

    def close(self) -> None:
        """Undo connect and close the connection.

        The connection will be unusable from this point forward; an Error (or subclass) exception will be raised if any operation is attempted with the connection, unless connect is call again."""
        self._connected = False

    def _check_connection(self, check_db=True) -> None:
        """Raise connection InterfaceError if not connected
        Defaults to check if a db is connected"""
        if not self._connected:
            raise InterfaceError("Client is not connected to a TerminusDB server.")
        if check_db and self.db is None:
            raise InterfaceError(
                "No database is connected. Please either connect to a database or create a new database."
            )

    def get_commit_history(self, max_history: int = 500) -> list:
        """Get the whole commit history.
        Commit history - Commit id, author of the commit, commit message and the commit time, in the current branch from the current commit, ordered backwards in time, will be returned in a dictionary in the follow format:
        {"commit_id":
            {"author": "commit_author",
             "message": "commit_message",
             "timestamp: <datetime object of the timestamp>" }
        }

        Parameters
        ----------
        max_history: int, optional
            maximum number of commit that would return, counting backwards from your current commit. Default is set to 500. It need to be nop-negitive, if input is 0 it will still give the last commit.

        Example
        -------
        >>> from terminusdb_client import WOQLClient
        >>> client = WOQLClient("https://127.0.0.1:6363"
        >>> client.connect(db="bank_balance_example")
        >>> client.get_commit_history()
        [{'commit': 's90wike9v5xibmrb661emxjs8k7ynwc', 'author': 'admin', 'message': 'Adding Jane', 'timstamp': datetime.da
        tetime(2020, 9, 3, 15, 29, 34)}, {'commit': '1qhge8qlodajx93ovj67kvkrkxsw3pg', 'author': 'gavin@terminusdb.com', 'm
        essage': 'Adding Jim', 'timstamp': datetime.datetime(2020, 9, 3, 15, 29, 33)}, {'commit': 'rciy1rfu5foj67ch00ow6f6n
        njjxe3i', 'author': 'gavin@terminusdb.com', 'message': 'Update mike', 'timstamp': datetime.datetime(2020, 9, 3, 15,
         29, 33)}, {'commit': 'n4d86u8juzx852r2ekrega5hl838ovh', 'author': 'gavin@terminusdb.com', 'message': 'Add mike', '
        timstamp': datetime.datetime(2020, 9, 3, 15, 29, 33)}, {'commit': '1vk2i8k8xce26p9jpi4zmq1h5vdqyuj', 'author': 'gav
        in@terminusdb.com', 'message': 'Label for balance was wrong', 'timstamp': datetime.datetime(2020, 9, 3, 15, 29, 33)
        }, {'commit': '9si4na9zv2qol9b189y92fia7ac3hbg', 'author': 'gavin@terminusdb.com', 'message': 'Adding bank account
        object to schema', 'timstamp': datetime.datetime(2020, 9, 3, 15, 29, 33)}, {'commit': '9egc4h0m36l5rbq1alr1fki6jbfu
        kuv', 'author': 'TerminusDB', 'message': 'internal system operation', 'timstamp': datetime.datetime(2020, 9, 3, 15,
         29, 33)}]

                Result
                ------
                list
        """
        if max_history < 0:
            raise ValueError("max_history needs to be non-negative.")
        if max_history > 1:
            limit_history = max_history - 1
        else:
            limit_history = 1
        woql_query = (
            WOQLQuery()
            .using("_commits")
            .limit(limit_history)
            .triple("v:branch", "name", WOQLQuery().string(self.branch))
            .triple("v:branch", "head", "v:commit")
            .path("v:commit", "parent*", "v:target_commit")
            .triple("v:target_commit", "identifier", "v:cid")
            .triple("v:target_commit", "author", "v:author")
            .triple("v:target_commit", "message", "v:message")
            .triple("v:target_commit", "timestamp", "v:timestamp")
        )
        # print(woql_query.to_dict())
        result = self.query(woql_query).get("bindings")
        if not result:
            return result
        else:
            result_list = []
            for result_item in result:
                result_list.append(
                    {
                        "commit": result_item["cid"]["@value"],
                        "author": result_item["author"]["@value"],
                        "message": result_item["message"]["@value"],
                        "timstamp": datetime.fromtimestamp(
                            int(result_item["timestamp"]["@value"])
                        ),
                    }
                )
            return result_list

    def _get_current_commit(self):
        woql_query = (
            WOQLQuery()
            .using("_commits")
            .triple("v:branch", "name", WOQLQuery().string(self.branch))
            .triple("v:branch", "head", "v:commit")
            .triple("v:commit", "identifier", "v:cid")
        )
        print(woql_query.to_dict())
        result = self.query(woql_query)
        if not result:
            return None
        current_commit = result.get("bindings")[0].get("cid").get("@value")
        return current_commit

    def _get_target_commit(self, step):
        woql_query = (
            WOQLQuery()
            .using("_commits")
            .path(
                "v:commit",
                f"parent{{{step},{step}}}",
                "v:target_commit",
            )
            .triple("v:branch", "name", WOQLQuery().string(self.branch))
            .triple("v:branch", "head", "v:commit")
            .triple("v:target_commit", "identifier", "v:cid")
        )
        print(woql_query.to_dict())
        result = self.query(woql_query)
        target_commit = result.get("bindings")[0].get("cid").get("@value")
        return target_commit

    def rollback(self, steps=1) -> None:
        """Curently not implementated. Please check back later.

        Raises
        ----------
        NotImplementedError
            Since TerminusDB currently does not support open transactions. This method is not applicable to it's usage. To reset commit head, use WOQLClient.reset

        """
        raise NotImplementedError(
            "Open transactions are currently not supported. To reset commit head, check WOQLClient.reset"
        )

    def copy(self) -> "WOQLClient":
        """Create a deep copy of this client.

        Returns
        -------
        WOQLClient
            The copied client instance.

        Examples
        --------
        >>> client = WOQLClient("https://127.0.0.1:6363/")
        >>> clone = client.copy()
        >>> assert client is not clone
        """
        return copy.deepcopy(self)

    def set_db(self, dbid: str, account: Optional[str] = None) -> str:
        """Set the connection to another database. This will reset the connection.

        Parameters
        ----------
        dbid : str
            Database identifer to set in the config.
        account : str
            User identifer to set in the config. If not passed in, it will use the current one.

        Returns
        -------
        str
            The current database identifier.

        Examples
        --------
        >>> client = WOQLClient("https://127.0.0.1:6363")
        >>> client.set_db("database1")
        'database1'
        """
        self._check_connection(check_db=False)

        if account is None:
            account = self.account

        return self.connect(
            account=account,
            db=dbid,
            remote_auth=self._remote_auth,
            key=self._key,
            user=self.user,
            branch=self.branch,
            ref=self.ref,
            repo=self.repo,
        )

    def resource(self, ttype: str, val: Optional[str] = None) -> str:
        """Create a resource identifier string based on the current config.

        Parameters
        ----------
        ttype : str
            Type of resource. One of ["db", "meta", "repo", "commits", "ref", "branch"].
        val : str, optional
            Branch or commit identifier.

        Returns
        -------
        str
            The constructed resource string.

        Examples
        --------
        >>> client = WOQLClient("https://127.0.0.1:6363")
        >>> client.account("<account>")
        '<account>'
        >>> client.db("<db>")
        '<db>'
        >>> client.repo("<repo>")
        '<repo>'
        >>> client.resource("db")
        '<account>/<db>/'
        >>> client.resource("meta")
        '<account>/<db>/_meta'
        >>> client.resource("commits")
        '<account>/<db>/<repo>/_commits'
        >>> client.resource("repo")
        '<account>/<db>/<repo>/_meta'
        >>> client.resource("ref", "<reference>")
        '<account>/<db>/<repo>/commit/<reference>'
        >>> client.resource("branch", "<branch>")
        '<account>/<db>/<repo>/branch/<branch>'
        """
        base = self.account + "/" + self.db + "/"
        if ttype == "db":
            return base
        elif ttype == "meta":
            return base + "_meta"
        base = base + self.repo
        if ttype == "repo":
            return base + "/_meta"
        elif ttype == "commits":
            return base + "/_commits"
        if val is None:
            if ttype == "ref":
                val = self.ref
            else:
                val = self.branch
        if ttype == "branch":
            return base + "/branch/" + val
        if ttype == "ref":
            return base + "/commit/" + val

    def _get_prefixes(self):
        """Get the prefixes for a given database"""
        self._check_connection()
        result = requests.get(
            self._db_base("prefixes"),
            auth=self._auth(),
        )
        return json.loads(_finish_reponse(result))
        # return self._dispatch_json("get", self._db_base("prefixes")).get("@context")

    def create_database(
        self,
        dbid: str,
        accountid: Optional[str] = None,
        label: Optional[str] = None,
        description: Optional[str] = None,
        prefixes: Optional[dict] = None,
        include_schema: bool = True,
    ) -> None:
        """Create a TerminusDB database by posting
        a terminus:Database document to the Terminus Server.

        Parameters
        ----------
        dbid : str
            Unique identifier of the database.
        accountid : str, optional
            ID of the organization in which to create the DB (defaults to 'admin')
        label : str, optional
            Database name.
        description : str, optional
            Database description.
        prefixes : dict, optional
            Optional dict containing ``"doc"`` and ``"scm"`` keys.

            doc (str)
                IRI to use when ``doc:`` prefixes are expanded. Defaults to ``terminusdb:///data``.
            scm (str)
                IRI to use when ``scm:`` prefixes are expanded. Defaults to ``terminusdb:///schema``.
        include_schema : bool
            If ``True``, a main schema graph will be created, otherwise only a main instance graph will be created.

        Raises
        ------
        InterfaceError
            if the client does not connect to a server

        Examples
        --------
        >>> client = WOQLClient("https://127.0.0.1:6363/")
        >>> client.create_database("someDB", "admin", "Database Label", "My Description")
        """

        self._check_connection(check_db=False)

        details: Dict[str, Any] = {}
        if label:
            details["label"] = label
        else:
            details["label"] = dbid
        if description:
            details["comment"] = description
        else:
            details["comment"] = ""
        if include_schema:
            details["schema"] = True
        if prefixes:
            details["prefixes"] = prefixes
        if accountid is None:
            accountid = self.account

        self.account = accountid
        self._connected = True
        self.db = dbid

        _finish_reponse(
            requests.post(
                self._db_url(),
                json=details,
                auth=self._auth(),
            )
        )

    def delete_database(
        self,
        dbid: Optional[str] = None,
        accountid: Optional[str] = None,
        force: bool = False,
    ) -> None:
        """Delete a TerminusDB database.

        If ``accountid`` is provided, then the account in the config will be updated
        and the new value will be used in future requests to the server.

        Parameters
        ----------
        dbid : str
            ID of the database to delete
        accountid : str, optional
            the account id in which the database resides (defaults to "admin")
        force: bool

        Raises
        ------
        UserWarning
            If the value of dbid is None.
        InterfaceError
            if the client does not connect to a server.

        Examples
        -------
        >>> client = WOQLClient("https://127.0.0.1:6363/")
        >>> client.delete_database("<database>", "<account>")
        """

        self._check_connection(check_db=False)

        if dbid is None:
            raise UserWarning(
                f"You are currently using the database: {self.account}/{self.db}. If you want to delete it, please do 'delete_database({self.db},{self.account})' instead."
            )

        self.db = dbid
        if accountid is None:
            warnings.warn(
                f"Delete Database Warning: You have not specify the accountid, assuming {self.account}/{self.db}"
            )
        else:
            self.account = accountid
        payload = {"force": force}
        _finish_reponse(
            requests.delete(
                self._db_url(),
                auth=self._auth(),
                params=payload,
            )
        )
        self.db = None

    def _validate_graph_type(self, graph_type):
        if graph_type not in ["instance", "schema"]:
            raise ValueError("graph_type can only be 'instance' or 'schema'")

    def get_triples(self, graph_type: str) -> str:
        """Retrieves the contents of the specified graph as triples encoded in turtle format

        Parameters
        ----------
        graph_type : str
            Graph type, either "instance" or "schema".

        Raises
        ------
        InterfaceError
            if the client does not connect to a database

        Returns
        -------
        str
        """

        self._check_connection()
        self._validate_graph_type(graph_type)
        result = requests.get(
            self._triples_url(graph_type),
            auth=self._auth(),
        )
        return json.loads(_finish_reponse(result))

    def update_triples(self, graph_type: str, turtle, commit_msg: str) -> None:
        """Updates the contents of the specified graph with the triples encoded in turtle format Replaces the entire graph contents

        Parameters
        ----------
        graph_type : str
            Graph type, either "instance" or "schema".
        turtle
            Valid set of triples in Turtle format.
        commit_msg : str
            Commit message.

        Raises
        ------
        InterfaceError
            if the client does not connect to a database
        """
        self._check_connection()
        self._validate_graph_type(graph_type)
        params = {"commit_info": self._generate_commit(commit_msg)}
        params["turtle"] = turtle
        result = requests.post(
            self._triples_url(graph_type),
            params=params,
            auth=self._auth(),
        )
        return json.loads(_finish_reponse(result))

    def insert_triples(
        self, graph_type: str, turtle, commit_msg: Optional[str] = None
    ) -> None:
        """Inserts into the specified graph with the triples encoded in turtle format.

        Parameters
        ----------
        graph_type : str
            Graph type, either "instance" or "schema".
        turtle
            Valid set of triples in Turtle format.
        commit_msg : str
            Commit message.

        Raises
        ------
        InterfaceError
            if the client does not connect to a database
        """
        self._check_connection()
        self._validate_graph_type(graph_type)
        params = {"commit_info": self._generate_commit(commit_msg)}
        params["turtle"] = turtle
        result = requests.put(
            self._triples_url(graph_type),
            params=params,
            auth=self._auth(),
        )
        return json.loads(_finish_reponse(result))

    def get_document(self, iri_id: str, graph_type: str = "instance", **kwargs) -> dict:
        """Retrieves the document of the iri_id

        Parameters
        ----------
        iri_id : str
            Iri id for the docuemnt that is retriving
        graph_type : str, optional
            Graph type, either "instance" or "schema".
        kwargs:
            Additional boolean flags for retriving. Currently avaliable: "prefixed", "minimized", "unfold"

        Raises
        ------
        InterfaceError
            if the client does not connect to a database

        Returns
        -------
        dict
        """
        self._validate_graph_type(graph_type)

        add_args = ["prefixed", "minimized", "unfold"]
        self._check_connection()
        payload = {"id": iri_id, "graph_type": graph_type}
        for the_arg in add_args:
            if the_arg in kwargs:
                payload[the_arg] = kwargs[the_arg]

        result = requests.get(
            self._documents_url(),
            params=payload,
            auth=self._auth(),
        )
        return json.loads(_finish_reponse(result))

    def get_documents_by_type(
        self,
        doc_type: str,
        graph_type: str = "instance",
        skip: int = 0,
        count: Optional[int] = None,
        **kwargs,
    ) -> Iterable:
        """Retrieves the documents by type

        Parameters
        ----------
        doc_type : str
            Specific type for the docuemnts that is retriving
        graph_type : str, optional
            Graph type, either "instance" or "schema".
        skip: int
            The starting posiion of the returning results, default to be 0
        count: int or None
            The maximum number of returned result, if None (default) it will return all of the avalible result.
        kwargs:
            Additional boolean flags for retriving. Currently avaliable: "prefixed", "unfold"

        Raises
        ------
        InterfaceError
            if the client does not connect to a database

        Returns
        -------
        iterable
            Stream of dictionaries
        """
        self._validate_graph_type(graph_type)

        add_args = ["prefixed", "unfold"]
        self._check_connection()
        payload = {"type": doc_type, "graph_type": graph_type}
        payload["skip"] = skip
        if count is not None:
            payload["count"] = count
        for the_arg in add_args:
            if the_arg in kwargs:
                payload[the_arg] = kwargs[the_arg]
        result = requests.get(
            self._documents_url(),
            params=payload,
            auth=self._auth(),
        )
        return _result2stream(_finish_reponse(result))

    def get_all_documents(
        self,
        graph_type: str = "instance",
        skip: int = 0,
        count: Optional[int] = None,
        **kwargs,
    ) -> Iterable:
        """Retrieves all avalibale the documents

        Parameters
        ----------
        graph_type : str, optional
            Graph type, either "instance" or "schema".
        skip: int
            The starting posiion of the returning results, default to be 0
        count: int or None
            The maximum number of returned result, if None (default) it will return all of the avalible result.
        kwargs:
            Additional boolean flags for retriving. Currently avaliable: "prefixed", "unfold"

        Raises
        ------
        InterfaceError
            if the client does not connect to a database

        Returns
        -------
        iterable
            Stream of dictionaries
        """
        self._validate_graph_type(graph_type)

        add_args = ["prefixed", "unfold"]
        self._check_connection()
        payload = {"graph_type": graph_type}
        payload["skip"] = skip
        if count is not None:
            payload["count"] = count
        for the_arg in add_args:
            if the_arg in kwargs:
                payload[the_arg] = kwargs[the_arg]
        result = requests.get(
            self._documents_url(),
            params=payload,
            auth=self._auth(),
        )
        return _result2stream(_finish_reponse(result))

    def _conv_to_dict(self, obj):
        if isinstance(obj, dict):
            return obj
        elif hasattr(obj, "to_dict"):
            return obj.to_dict()
        elif hasattr(obj, "_to_dict"):
            if hasattr(obj, "_isinstance") and obj._isinstance:
                return obj._obj_to_dict()
            else:
                return obj._to_dict()
        else:
            raise ValueError("Object cannot convert to dictionary")

    def insert_document(
        self,
        document: Union[
            dict,
            List[dict],
            "WOQLSchema",  # noqa:F821
            "DocumentTemplate",  # noqa:F821
            List["DocumentTemplate"],  # noqa:F821
        ],
        graph_type: str = "instance",
        commit_msg: Optional[str] = None,
    ) -> None:
        """Inserts the specified document(s)

        Parameters
        ----------
        document: dict or list of dict
            Document(s) to be inserted.
        graph_type : str
            Graph type, either "inference", "instance" or "schema".
        commit_msg : str
            Commit message.

        Raises
        ------
        InterfaceError
            if the client does not connect to a database

        Returns
        -------
        list
            list of ids of the inseted docuemnts
        """
        self._validate_graph_type(graph_type)
        self._check_connection()
        params = self._generate_commit(commit_msg)
        params["graph_type"] = graph_type

        if isinstance(document, list):
            new_doc = []
            for item in document:
                item_dict = self._conv_to_dict(item)
                new_doc.append(item_dict)
            document = new_doc
        else:
            document = self._conv_to_dict(document)
        result = requests.post(
            self._documents_url(),
            params=params,
            json=document,
            auth=self._auth(),
        )
        return json.loads(_finish_reponse(result))

    def replace_document(
        self,
        document: Union[
            dict,
            List[dict],
            "WOQLSchema",  # noqa:F821
            "DocumentTemplate",  # noqa:F821
            List["DocumentTemplate"],  # noqa:F821
        ],
        graph_type: str = "instance",
        commit_msg: Optional[str] = None,
    ) -> None:
        """Updates the specified document(s)

        Parameters
        ----------
        document: dict or list of dict
            Document(s) to be updated.
        graph_type : str
            Graph type, either "instance" or "schema".
        commit_msg : str
            Commit message.

        Raises
        ------
        InterfaceError
            if the client does not connect to a database
        """
        self._validate_graph_type(graph_type)
        self._check_connection()
        params = self._generate_commit(commit_msg)
        params["graph_type"] = graph_type

        if isinstance(document, list):
            new_doc = []
            for item in document:
                # while document:
                #     item = document.pop()
                item_dict = self._conv_to_dict(item)
                new_doc.append(item_dict)
                # id_list.append(item_dict['@id'])
            document = new_doc
        else:
            document = self._conv_to_dict(document)
        _finish_reponse(
            requests.put(
                self._documents_url(),
                params=params,
                json=document,
                auth=self._auth(),
            )
        )

    def update_document(
        self,
        document: Union[
            dict,
            List[dict],
            "WOQLSchema",  # noqa:F821
            "DocumentTemplate",  # noqa:F821
            List["DocumentTemplate"],  # noqa:F821
        ],
        graph_type: str = "instance",
        commit_msg: Optional[str] = None,
    ) -> None:

        self._validate_graph_type(graph_type)
        self._check_connection()

        all_existing_obj = self.get_all_documents(graph_type=graph_type)
        all_existing_id = list(map(lambda x: x.get("@id"), all_existing_obj))
        insert_docs = []
        update_docs = []
        if isinstance(document, list):
            update_list = document
        elif hasattr(document, "all_obj"):
            update_list = document.all_obj()
        else:
            update_list = [document]

        for obj in update_list:
            if hasattr(obj, "_id"):
                obj_id = obj._id
            elif hasattr(obj, "_to_dict"):
                obj_id = obj._to_dict().get("@id")
            else:
                obj_id = obj.get("@id")

            if obj_id is not None and obj_id in all_existing_id:
                update_docs.append(obj)
            else:
                insert_docs.append(obj)

        if graph_type == "schema":
            stuff = "Schema object"
        elif graph_type == "instance":
            stuff = "Document object"

        self.insert_document(
            insert_docs,
            commit_msg=f"{stuff} inserted by Python client.",
            graph_type=graph_type,
        )
        self.replace_document(
            update_docs,
            commit_msg=f"{stuff} updated by Python client.",
            graph_type=graph_type,
        )

    def delete_document(
        self,
        doc_id: Union[str, List[str]],
        graph_type: str = "instance",
        commit_msg: Optional[str] = None,
    ) -> None:
        """Delete the specified document(s)

        Parameters
        ----------
        doc_id: str or list of str
            Id(s) of document(s) to be updated.
        graph_type : str
            Graph type, either "instance" or "schema".
        commit_msg : str
            Commit message.

        Raises
        ------
        InterfaceError
            if the client does not connect to a database
        """
        self._validate_graph_type(graph_type)
        self._check_connection()
        params = self._generate_commit(commit_msg)
        params["graph_type"] = graph_type
        _finish_reponse(
            requests.delete(
                self._documents_url(),
                params=params,
                json=doc_id,
                auth=self._auth(),
            )
        )

    def has_doc(self, doc_id: str, graph_type: str = "instance") -> bool:
        """Check if a certain document exist in a database

        Parameters
        ----------
        doc_id: str
            Id of document to be checked.
        graph_type : str
            Graph type, either "instance" or "schema".

        returns
        -------
        Bool
            if the document exist
        """
        self._validate_graph_type(graph_type)
        self._check_connection()
        all_existing_obj = self.get_all_documents(graph_type=graph_type)
        all_existing_id = list(map(lambda x: x.get("@id"), all_existing_obj))
        return doc_id in all_existing_id

    def get_class_frame(self, class_name):
        """Get the frame of the class of class_name. Provide information about all the avaliable properties of that class.

        Parameters
        ----------
        class_name: str
            Name of the class

        returns
        -------
        dict
            Dictionary containing information
        """
        self._check_connection()
        opts = {"type": class_name}
        result = requests.get(
            self._class_frame_url(),
            params=opts,
            auth=self._auth(),
        )
        return json.loads(_finish_reponse(result))

    def commit(self):
        """Not implementated: open transactions currently not suportted. Please check back later."""

    def query(
        self,
        woql_query: Union[dict, WOQLQuery],
        commit_msg: Optional[str] = None,
        # file_dict: Optional[dict] = None,
    ) -> Union[dict, str]:
        """Updates the contents of the specified graph with the triples encoded in turtle format Replaces the entire graph contents

        Parameters
        ----------
        woql_query : dict or WOQLQuery object
            A woql query as an object or dict
        commit_mg : str
            A message that will be written to the commit log to describe the change
        file_dict: **deprecated**
            File dictionary to be associated with post name => filename, for multipart POST

        Raises
        ------
        InterfaceError
            if the client does not connect to a database

        Examples
        -------
        >>> WOQLClient(server="http://localhost:6363").query(woql, "updating graph")

        Returns
        -------
        dict
        """
        self._check_connection()
        query_obj = {"commit_info": self._generate_commit(commit_msg)}
        if isinstance(woql_query, WOQLQuery):
            request_woql_query = woql_query.to_dict()
        else:
            request_woql_query = woql_query
        query_obj["query"] = request_woql_query

        result = requests.post(
            self._query_url(),
            json=query_obj,
            auth=self._auth(),
        )
        fin_reqult = json.loads(_finish_reponse(result))

        if fin_reqult.get("inserts") or fin_reqult.get("deletes"):
            return "Commit successfully made."
        return fin_reqult

    def create_branch(self, new_branch_id: str, empty: bool = False) -> None:
        """Create a branch starting from the current branch.

        Parameters
        ----------
        new_branch_id : str
            New branch identifier.
        empty : bool
            Create an empty branch if true (no starting commit)

        Raises
        ------
        InterfaceError
            if the client does not connect to a database
        """
        self._check_connection()
        if empty:
            source = {}
        elif self.ref:
            source = {
                "origin": f"{self.account}/{self.db}/{self.repo}/commit/{self.ref}"
            }
        else:
            source = {
                "origin": f"{self.account}/{self.db}/{self.repo}/branch/{self.branch}"
            }

        _finish_reponse(
            requests.post(
                self._branch_url(new_branch_id),
                json=source,
                auth=self._auth(),
            )
        )

    def pull(
        self,
        remote: str = "origin",
        remote_branch: Optional[str] = None,
        message: Optional[str] = None,
        author: Optional[str] = None,
    ) -> dict:
        """Pull updates from a remote repository to the current database.

        Parameters
        ----------
        remote: str
            remote to pull from, default "origin"
        remote_branch: str, optional
            remote branch to pull from, default to be your current barnch
        message: str, optional
            optional commit message
        author: str, optional
            option to overide the author of the operation

        Raises
        ------
        InterfaceError
            if the client does not connect to a database

        Returns
        -------
        dict

        Examples
        --------
        >>> client = WOQLClient("https://127.0.0.1:6363/")
        >>> client.pull()
        """
        self._check_connection()
        if remote_branch is None:
            remote_branch = self.branch
        if author is None:
            author = self.author
        if message is None:
            message = (
                f"Pulling from {remote}/{remote_branch} by Python client {__version__}"
            )
        rc_args = {
            "remote": remote,
            "remote_branch": remote_branch,
            "author": author,
            "message": message,
        }

        result = requests.post(
            self._pull_url(),
            json=rc_args,
            auth=self._auth(),
        )

        return json.loads(_finish_reponse(result))

    def fetch(self, remote_id: str) -> dict:
        """Fatch the brach from a remote

        Parameters
        ----------
        remote_id: str
            id of the remote

        Raises
        ------
        InterfaceError
            if the client does not connect to a database"""
        self._check_connection()

        result = requests.post(
            self._fetch_url(remote_id),
            auth=self._auth(),
        )

        return json.loads(_finish_reponse(result))

    def push(
        self,
        remote: str = "origin",
        remote_branch: Optional[str] = None,
        message: Optional[str] = None,
        author: Optional[str] = None,
    ) -> dict:
        """Push changes from a branch to a remote repo

        Parameters
        ----------
        remote: str
            remote to push to, default "origin"
        remote_branch: str, optional
            remote branch to push to, default to be your current barnch
        message: str, optional
            optional commit message
        author: str, optional
            option to overide the author of the operation

        Raises
        ------
        InterfaceError
            if the client does not connect to a database

        Examples
        -------
        >>> WOQLClient(server="http://localhost:6363").push(remote="origin", remote_branch = "main", author = "admin", message = "commit message"})

        Returns
        -------
        dict
        """
        self._check_connection()
        if remote_branch is None:
            remote_branch = self.branch
        if author is None:
            author = self._author
        if message is None:
            message = (
                f"Pushing to {remote}/{remote_branch} by Python client {__version__}"
            )
        rc_args = {
            "remote": remote,
            "remote_branch": remote_branch,
            "author": author,
            "message": message,
        }

        result = requests.post(
            self._push_url(),
            json=rc_args,
            auth=self._auth(),
        )

        return json.loads(_finish_reponse(result))

    def rebase(
        self,
        rebase_source: str,
        message: Optional[str] = None,
        author: Optional[str] = None,
    ) -> dict:
        """Rebase the current branch onto the specified remote branch.

        Notes
        -----
        The "remote" repo can live in the local database.

        Parameters
        ----------
        rebase_source : str
            the source branch for the rebase
        message : str, optional
            the commit message
        author : str, optional
            the commit author

        Raises
        ------
        InterfaceError
            if the client does not connect to a database

        Returns
        -------
        dict

        Examples
        --------
        >>> client = WOQLClient("https://127.0.0.1:6363/")
        >>> client.rebase("the_branch")
        """
        self._check_connection()

        if author is None:
            author = self._author
        if message is None:
            message = f"Rebase from {rebase_source} by Python client {__version__}"
        rc_args = {"rebase_from": rebase_source, "author": author, "message": message}

        result = requests.post(
            self._rebase_url(),
            json=rc_args,
            auth=self._auth(),
        )

        return json.loads(_finish_reponse(result))

    def reset(self, commit: str, use_path: bool = False) -> None:
        """Reset the current branch HEAD to the specified commit path. Doing it will reset the internal commit counter (self._commit_made) back to zero.

        Raises
        ------
        InterfaceError
            if the client does not connect to a database

        Notes
        -----
        The "remote" repo can live in the local database.

        Parameters
        ----------
        commit: string
            Commit id or path to the commit (if use_path is True), for instance '234980523ffaf93' or 'admin/database/local/commit/234980523ffaf93'.
        use_path : bool
            Wheather or not the commit given is an id or path. Default using id and use_path is False.

        Examples
        --------
        >>> client = WOQLClient("https://127.0.0.1:6363/")
        >>> client.checkout("some_branch")
        >>> client.reset('234980523ffaf93')
        >>> client.reset('admin/database/local/commit/234980523ffaf93', use_path=True)
        """

        self._check_connection()
        if use_path:
            commit_path = commit
        else:
            commit_path = f"{self.account}/{self.db}/{self.repo}/commit/{commit}"

        _finish_reponse(
            requests.post(
                self._reset_url(),
                json={"commit_descriptor": commit_path},
                auth=self._auth(),
            )
        )

    def optimize(self, path: str) -> None:
        """Optimize the specified path.

        Raises
        ------
        InterfaceError
            if the client does not connect to a database

        Notes
        -----
        The "remote" repo can live in the local database.

        Parameters
        ----------
        path : string
            Path to optimize, for instance admin/database/_meta for the repo graph.

        Examples
        --------
        >>> client = WOQLClient("https://127.0.0.1:6363/")
        >>> client.optimize('admin/database/_meta')
        """
        self._check_connection()

        _finish_reponse(
            requests.post(
                self._optimize_url(path),
                auth=self._auth(),
            )
        )

    def squash(
        self, message: Optional[str] = None, author: Optional[str] = None
    ) -> dict:
        """Squash the current branch HEAD into a commit

        Raises
        ------
        InterfaceError
            if the client does not connect to a database

        Notes
        -----
        The "remote" repo can live in the local database.

        Parameters
        ----------
        message : string
            Message for the newly created squash commit
        author : string
            Author of the commit

        Returns
        -------
        dict
            A dict with the new commit id:
            {'@type' : 'api:SquashResponse',
             'api:commit' : Commit,
             'api:old_commit' : Old_Commit,
             'api:status' : "api:success"}

        Examples
        --------
        >>> client = WOQLClient("https://127.0.0.1:6363/")
        >>> client.connect(user="admin", key="root", account="admin", db="some_db")
        >>> client.squash('This is a squash commit message!')
        """
        self._check_connection()

        result = requests.post(
            self._squash_url(),
            json={"commit_info": self._generate_commit(message, author)},
            auth=self._auth(),
        )

        return json.loads(_finish_reponse(result))

    def clonedb(
        self, clone_source: str, newid: str, description: Optional[str] = None
    ) -> None:
        """Clone a remote repository and create a local copy.

        Parameters
        ----------
        clone_source : str
            The source url of the repo to be cloned.
        newid : str
            Identifier of the new repository to create.
        Description : str, optional
            Optional description about the cloned database.

        Raises
        ------
        InterfaceError
            if the client does not connect to a database

        Examples
        --------
        >>> client = WOQLClient("https://127.0.0.1:6363/")
        >>> client.clonedb("http://terminusdb.com/some_user/test_db", "my_test_db")
        """
        self._check_connection()
        if description is None:
            description = f"New database {newid}"
        rc_args = {"remote_url": clone_source, "label": newid, "comment": description}

        _finish_reponse(
            requests.post(
                self._clone_url(newid),
                json=rc_args,
                auth=self._auth(),
            )
        )

    def _generate_commit(
        self, msg: Optional[str] = None, author: Optional[str] = None
    ) -> dict:
        """Pack the specified commit info into a dict format expected by the server.

        Parameters
        ----------
        msg : str
            Commit message.
        author : str
            Commit author.

        Returns
        -------
        dict
            Formatted commit info.

        Examples
        --------
        >>> client = WOQLClient("https://127.0.0.1:6363/")
        >>> client._generate_commit("<message>", "<author>")
        {'author': '<author>', 'message': '<message>'}
        """
        if author:
            mes_author = author
        else:
            mes_author = self._author
        if not msg:
            msg = f"Commit via python client {__version__}"
        return {"author": mes_author, "message": msg}

    def _auth(self):
        # if https basic
        if not self._jwt_token and self._connected and self._key and self.user:
            return (self.user, self._key)
        return JWTAuth(self._jwt_token)
        # TODO: remote_auth

    def get_database(self, dbid: str) -> Optional[dict]:
        """
        Returns metadata (id, organization, label, comment) about the requested database
        Parameters
        ----------
        dbid : str
            The id of the database
        account : str
            The account / organization id that the user is acting through

        Raises
        ------
        InterfaceError
            if the client does not connect to a server

        Returns
        -------
        dict or None if not found
        """
        self._check_connection(check_db=False)
        for this_db in self.get_databases():
            if this_db["name"] == dbid:
                return this_db
        return None

    def get_databases(self) -> List[dict]:
        """
        Returns a list of database metadata records for all databases the user has access to

        Raises
        ------
        InterfaceError
            if the client does not connect to a server

        Returns
        -------
        list of dicts
        """
        self._check_connection(check_db=False)

        result = requests.get(
            self.api,
            auth=self._auth(),
        )
        return json.loads(_finish_reponse(result))

    def list_databases(self) -> List[Dict]:
        """
        Returns a list of database ids for all databases the user has access to

        Raises
        ------
        InterfaceError
            if the client does not connect to a server

        Returns
        -------
        list of dicts
        """
        self._check_connection(check_db=False)
        all_dbs = []
        for data in self.get_databases():
            all_dbs.append(data["name"])
        return all_dbs

    def _db_url_fragment(self):
        if self.db == "_system":
            return self.db
        return f"{self.account}/{self.db}"

    def _db_base(self, action: str):
        return f"{self.api}/{action}/{self._db_url_fragment()}"

    def _branch_url(self, branch_id: str):
        base_url = self._repo_base("branch")
        return f"{base_url}/branch/{branch_id}"

    def _repo_base(self, action: str):
        return self._db_base(action) + f"/{self.repo}"

    def _branch_base(self, action: str):
        base = self._repo_base(action)
        if self.repo == "_meta":
            return base
        if self.branch == "_commits":
            return base + f"/{self.branch}"
        elif self.ref:
            return base + f"/commit/{self.ref}"
        else:
            return base + f"/branch/{self.branch}"
        return base

    def _query_url(self):
        if self.db == "_system":
            return self._db_base("woql")
        return self._branch_base("woql")

    def _class_frame_url(self):
        if self.db == "_system":
            return self._db_base("schema")
        return self._branch_base("schema")

    def _documents_url(self):
        if self.db == "_system":
            base_url = self._db_base("document")
        else:
            base_url = self._branch_base("document")
        return base_url

    def _triples_url(self, graph_type="instance"):
        if self.db == "_system":
            base_url = self._db_base("triples")
        else:
            base_url = self._branch_base("triples")
        return f"{base_url}/{graph_type}"

    def _clone_url(self, new_repo_id: str):
        return f"{self.api}/clone/{self.account}/{new_repo_id}"

    def _cloneable_url(self):
        crl = f"{self.server_url}/{self.account}/{self.db}"
        return crl

    def _pull_url(self):
        return self._branch_base("pull")

    def _fetch_url(self, remote_name: str):
        furl = self._branch_base("fetch")
        return furl + "/" + remote_name + "/_commits"

    def _rebase_url(self):
        return self._branch_base("rebase")

    def _reset_url(self):
        return self._branch_base("reset")

    def _optimize_url(self, path: str):
        return f"{self.api}/optimize/{path}"

    def _squash_url(self):
        return self._branch_base("squash")

    def _push_url(self):
        return self._branch_base("push")

    def _db_url(self):
        return self._db_base("db")
