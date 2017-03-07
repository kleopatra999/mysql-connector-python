# -*- coding: utf-8 -*-
# MySQL Connector/Python - MySQL driver written in Python.
# Copyright (c) 2016, 2017, Oracle and/or its affiliates. All rights reserved.

# MySQL Connector/Python is licensed under the terms of the GPLv2
# <http://www.gnu.org/licenses/old-licenses/gpl-2.0.html>, like most
# MySQL Connectors. There are special exceptions to the terms and
# conditions of the GPLv2 as it is applied to this software, see the
# FOSS License Exception
# <http://www.mysql.com/about/legal/licensing/foss-exception.html>.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

"""Unittests for mysqlx.connection
"""

import logging
import unittest
import sys
import tests
import mysqlx

if mysqlx.compat.PY3:
    from urllib.parse import quote_plus
else:
    from urllib import quote_plus

LOGGER = logging.getLogger(tests.LOGGER_NAME)

_URI_TEST_RESULTS = (  # (uri, result)
    ("127.0.0.1", None),
    ("localhost", None),
    ("domain.com", None),
    ("user:password@127.0.0.1", {"schema": "", "host": "127.0.0.1",
                                 "password": "password", "port": 33060,
                                 "user": "user"}),
    ("user:password@127.0.0.1:33061", {"schema": "", "host": "127.0.0.1",
                                       "password": "password", "port": 33061,
                                       "user": "user"}),
    ("user:@127.0.0.1", {"schema": "", "host": "127.0.0.1", "password": "",
                         "port": 33060, "user": "user"}),
    ("user:@127.0.0.1/schema", {"schema": "schema", "host": "127.0.0.1",
                                "password": "", "port": 33060,
                                "user": "user"}),
    ("mysqlx://user:@127.0.0.1", {"schema": "", "host": "127.0.0.1",
                                  "password": "", "port": 33060,
                                  "user": "user"}),
    ("mysqlx://user:@127.0.0.1:33060/schema",
     {"schema": "schema", "host": "127.0.0.1", "password": "", "port": 33060,
      "user": "user"}),
    ("mysqlx://user@[2001:db8:85a3:8d3:1319:8a2e:370:7348]:1", None),
    ("mysqlx://user:password@[2001:db8:85a3:8d3:1319:8a2e:370:7348]:1",
     {"schema": "", "host": "2001:db8:85a3:8d3:1319:8a2e:370:7348",
      "password": "password", "port": 1, "user": "user"}),
    ("mysqlx://user:password@[2001:db8:85a3:8d3:1319:8a2e:370:7348]:1/schema",
     {"schema": "schema", "host": "2001:db8:85a3:8d3:1319:8a2e:370:7348",
      "password": "password", "port": 1, "user": "user"}),
    ("áé'í'óú:unicode@127.0.0.1",
     {"schema": "", "host": "127.0.0.1", "password": "unicode",
      "port": 33060, "user": "áé'í'óú"}),
    ("unicode:áé'í'óú@127.0.0.1",
     {"schema": "", "host": "127.0.0.1", "password": "áé'í'óú",
      "port": 33060, "user": "unicode"}),
    ("root:@[localhost, 127.0.0.1:88, [::]:99, [a1:b1::]]",
     {"routers": [{"host": "localhost", "port": 33060},
                  {"host": "127.0.0.1", "port": 88},
                  {"host": "::", "port": 99},
                  {"host": "a1:b1::", "port": 33060}],
      "user": "root", "password": "", "schema": ""}),
     ("root:@[a1:a2:a3:a4:a5:a6:a7:a8]]",
      {"host": "a1:a2:a3:a4:a5:a6:a7:a8", "schema": "",
              "port": 33060, "user": "root", "password": ""}),
     ("root:@localhost", {"user": "root", "password": "",
      "host": "localhost", "port": 33060, "schema": ""}),
     ("root:@[a1:b1::]", {"user": "root", "password": "",
      "host": "a1:b1::", "port": 33060, "schema": ""}),
     ("root:@[a1:b1::]:88", {"user": "root", "password": "",
      "host": "a1:b1::", "port": 88, "schema": ""}),
     ("root:@[[a1:b1::]:88]", {"user": "root", "password": "",
      "routers": [{"host": "a1:b1::", "port":88}], "schema": ""}),
     ("root:@[(address=localhost:99, priority=99)]",
      {"user": "root", "password": "", "schema": "",
      "routers": [{"host": "localhost", "port": 99, "priority": 99}]})
)


_ROUTER_LIST_RESULTS = (  # (uri, result)
    ("áé'í'óú:unicode@127.0.0.1", {"schema": "", "host": "127.0.0.1",
     "port": 33060, "password": "unicode", "user": "áé'í'óú"}),
    ("unicode:áé'í'óú@127.0.0.1", {"schema": "", "host": "127.0.0.1",
     "port": 33060, "password": "áé'í'óú", "user": "unicode"}),
    ("user:password@[127.0.0.1, localhost]", {"schema": "", "routers":
     [{"host": "127.0.0.1", "port": 33060}, {"host": "localhost", "port":
     33060}], "password": "password", "user": "user"}),
    ("user:password@[(address=127.0.0.1, priority=99), (address=localhost,"
     "priority=98)]", {"schema": "", "routers": [{"host": "127.0.0.1",
     "port": 33060, "priority": 99}, {"host": "localhost", "port": 33060,
     "priority": 98}], "password": "password", "user": "user"}),
)

def build_uri(**kwargs):
    uri = "mysqlx://{0}:{1}".format(kwargs["user"], kwargs["password"])

    if "host" in kwargs:
        host = "[{0}]".format(kwargs["host"]) \
                if ":" in kwargs["host"] else kwargs["host"]
        uri = "{0}@{1}".format(uri, host)
    elif "routers" in kwargs:
        routers = []
        for router in kwargs["routers"]:
            fmt = "(address={host}{port}, priority={priority})" \
                   if "priority" in router else "{host}{port}"
            host = "[{0}]".format(router["host"]) if ":" in router["host"] \
                    else router["host"]
            port = ":{0}".format(router["port"]) if "port" in router else ""

            routers.append(fmt.format(host=host, port=port,
                                      priority=router.get("priority", None)))

        uri = "{0}@[{1}]".format(uri, ",".join(routers))
    else:
        raise mysqlx.errors.ProgrammingError("host or routers required.")

    if "port" in kwargs:
        uri = "{0}:{1}".format(uri, kwargs["port"])
    if "schema" in kwargs:
        uri = "{0}/{1}".format(uri, kwargs["schema"])

    query = []
    if "ssl_ca" in kwargs:
        query.append("ssl-ca={0}".format(kwargs["ssl_ca"]))
    if "ssl_cert" in kwargs:
        query.append("ssl-cert={0}".format(kwargs["ssl_cert"]))
    if "ssl_key" in kwargs:
        query.append("ssl-key={0}".format(kwargs["ssl_key"]))

    if len(query) > 0:
        uri = "{0}?{1}".format(uri, "&".join(query))

    return uri


@unittest.skipIf(tests.MYSQL_VERSION < (5, 7, 12), "XPlugin not compatible")
class MySQLxXSessionTests(tests.MySQLxTests):

    def setUp(self):
        self.connect_kwargs = tests.get_mysqlx_config()
        self.schema_name = self.connect_kwargs["schema"]
        try:
            self.session = mysqlx.get_session(self.connect_kwargs)
        except mysqlx.Error as err:
            self.fail("{0}".format(err))

    def test___init__(self):
        bad_config = {
            "host": "bad_host",
            "port": "",
            "username": "root",
            "password": ""
        }
        self.assertRaises(TypeError, mysqlx.XSession, bad_config)

        host = self.connect_kwargs["host"]
        port = self.connect_kwargs["port"]
        user = self.connect_kwargs["user"]
        password = self.connect_kwargs["password"]

        # XSession to a farm using one of many routers (prios)
        # Loop during connect because of network error (succeed)
        routers = [{"host": "bad_host","priority": 100},
                   {"host": host, "port": port, "priority": 98}]
        uri = build_uri(user=user, password=password, routers=routers)
        session = mysqlx.get_session(uri)
        session.close()

        # XSession to a farm using one of many routers (incomplete prios)
        routers = [{"host": "bad_host", "priority": 100},
                   {"host": host, "port": port}]
        uri = build_uri(user=user, password=password, routers=routers)
        self.assertRaises(mysqlx.errors.ProgrammingError,
                          mysqlx.get_session, uri)
        try:
            session = mysqlx.get_session(uri)
        except mysqlx.errors.ProgrammingError as err:
            self.assertEqual(4000, err.errno)

        # XSession to a farm using invalid priorities (out of range)
        routers = [{"host": "bad_host", "priority": 100},
                   {"host": host, "port": port, "priority": 101}]
        uri = build_uri(user=user, password=password, routers=routers)
        self.assertRaises(mysqlx.errors.ProgrammingError,
                          mysqlx.get_session, uri)
        try:
            session = mysqlx.get_session(uri)
        except mysqlx.errors.ProgrammingError as err:
            self.assertEqual(4007, err.errno)

        # Establish an XSession to a farm using one of many routers (no prios)
        routers = [{"host": "bad_host"}, {"host": host, "port": port}]
        uri = build_uri(user=user, password=password, routers=routers)
        session = mysqlx.get_session(uri)
        session.close()

        # Break loop during connect (non-network error)
        uri = build_uri(user=user, password="bad_pass", routers=routers)
        self.assertRaises(mysqlx.errors.InterfaceError,
                          mysqlx.get_session, uri)

        # Break loop during connect (none left)
        uri = "mysqlx://{0}:{1}@[bad_host, another_bad_host]".format(user, password)
        self.assertRaises(mysqlx.errors.InterfaceError,
                          mysqlx.get_session, uri)
        try:
            session = mysqlx.get_session(uri)
        except mysqlx.errors.InterfaceError as err:
            self.assertEqual(4001, err.errno)

    @unittest.skipIf(tests.MYSQL_VERSION < (5, 7, 15), "--mysqlx-socket option tests not available for this MySQL version")
    def test_mysqlx_socket(self):
        # Connect with unix socket
        uri = "mysqlx://{user}:{password}@({socket})".format(
            user=self.connect_kwargs["user"],
            password=self.connect_kwargs["password"],
            socket=self.connect_kwargs["socket"])

        session = mysqlx.get_session(uri)

        conn = mysqlx._get_connection_settings("root:@(/path/to/sock)")
        self.assertEqual("/path/to/sock", conn["socket"])
        self.assertEqual("", conn["schema"])

        conn = mysqlx._get_connection_settings("root:@(/path/to/sock)/schema")
        self.assertEqual("/path/to/sock", conn["socket"])
        self.assertEqual("schema", conn["schema"])

        conn = mysqlx._get_connection_settings("root:@/path%2Fto%2Fsock")
        self.assertEqual("/path/to/sock", conn["socket"])
        self.assertEqual("", conn["schema"])

        conn = mysqlx._get_connection_settings("root:@/path%2Fto%2Fsock/schema")
        self.assertEqual("/path/to/sock", conn["socket"])
        self.assertEqual("schema", conn["schema"])

        conn = mysqlx._get_connection_settings("root:@.%2Fpath%2Fto%2Fsock")
        self.assertEqual("./path/to/sock", conn["socket"])
        self.assertEqual("", conn["schema"])

        conn = mysqlx._get_connection_settings("root:@.%2Fpath%2Fto%2Fsock"
                                               "/schema")
        self.assertEqual("./path/to/sock", conn["socket"])
        self.assertEqual("schema", conn["schema"])

        conn = mysqlx._get_connection_settings("root:@..%2Fpath%2Fto%2Fsock")
        self.assertEqual("../path/to/sock", conn["socket"])
        self.assertEqual("", conn["schema"])

        conn = mysqlx._get_connection_settings("root:@..%2Fpath%2Fto%2Fsock"
                                               "/schema")
        self.assertEqual("../path/to/sock", conn["socket"])
        self.assertEqual("schema", conn["schema"])


    def test_connection_uri(self):
        uri = build_uri(user=self.connect_kwargs["user"],
                         password=self.connect_kwargs["password"],
                         host=self.connect_kwargs["host"],
                         port=self.connect_kwargs["port"],
                         schema=self.connect_kwargs["schema"])
        session = mysqlx.get_session(uri)
        self.assertIsInstance(session, mysqlx.XSession)

        # Test URI parser function
        for uri, res in _ROUTER_LIST_RESULTS:
            try:
                settings = mysqlx._get_connection_settings(uri)
                self.assertEqual(res, settings)
            except mysqlx.Error:
                self.assertEqual(res, None)

    def test_get_schema(self):
        schema = self.session.get_schema(self.schema_name)
        self.assertTrue(schema, mysqlx.Schema)
        self.assertEqual(schema.get_name(), self.schema_name)

    def test_get_default_schema(self):
        schema = self.session.get_default_schema()
        self.assertTrue(schema, mysqlx.Schema)
        self.assertEqual(schema.get_name(), self.connect_kwargs["schema"])

        # Test without default schema configured at connect time
        settings = self.connect_kwargs.copy()
        settings["schema"] = None
        session = mysqlx.get_session(settings)
        self.assertRaises(mysqlx.ProgrammingError, session.get_default_schema)
        session.close()

    def test_drop_schema(self):
        test_schema = 'mysql_xsession_test_drop_schema'
        schema = self.session.create_schema(test_schema)

        self.session.drop_schema(test_schema)
        self.assertFalse(schema.exists_in_database())

    def test_create_schema(self):
        schema = self.session.create_schema(self.schema_name)
        self.assertTrue(schema.exists_in_database())

    def test_close(self):
        session = mysqlx.get_session(self.connect_kwargs)
        schema = session.get_schema(self.schema_name)

        session.close()
        self.assertRaises(mysqlx.OperationalError, schema.exists_in_database)

    def test_bind_to_default_shard(self):
        try:
            # Getting a NodeSession to the default shard
            sess = mysqlx.get_session(self.connect_kwargs)
            nsess = sess.bind_to_default_shard()
            self.assertEqual(sess._settings, nsess._settings)

            # Close XSession and all dependent NodeSessions
            sess.close()
            self.assertFalse(nsess.is_open())

            # Connection error on XSession
            sess = mysqlx.get_session(self.connect_kwargs)
            nsess_a = sess.bind_to_default_shard()
            nsess_b = sess.bind_to_default_shard()
            tests.MYSQL_SERVERS[0].stop()
            tests.MYSQL_SERVERS[0].wait_down()

            self.assertRaises(mysqlx.errors.InterfaceError,
                              sess.get_default_schema().exists_in_database)
            self.assertFalse(sess.is_open())
            self.assertFalse(nsess_a.is_open())
            self.assertFalse(nsess_b.is_open())

            tests.MYSQL_SERVERS[0].start()
            tests.MYSQL_SERVERS[0].wait_up()

            # Connection error on dependent NodeSession
            sess = mysqlx.get_session(self.connect_kwargs)
            nsess_a = sess.bind_to_default_shard()
            nsess_b = sess.bind_to_default_shard()
            tests.MYSQL_SERVERS[0].stop()
            tests.MYSQL_SERVERS[0].wait_down()

            self.assertRaises(mysqlx.errors.InterfaceError,
                              nsess_a.sql("SELECT 1").execute)
            self.assertFalse(nsess_a.is_open())
            self.assertTrue(nsess_b.is_open())
            self.assertTrue(sess.is_open())

            tests.MYSQL_SERVERS[0].start()
            tests.MYSQL_SERVERS[0].wait_up()

            # Getting a NodeSession a shard (connect error)
            sess = mysqlx.get_session(self.connect_kwargs)
            tests.MYSQL_SERVERS[0].stop()
            tests.MYSQL_SERVERS[0].wait_down()

            self.assertRaises(mysqlx.errors.InterfaceError,
                              sess.bind_to_default_shard)

            tests.MYSQL_SERVERS[0].start()
            tests.MYSQL_SERVERS[0].wait_up()

        finally:
            if not tests.MYSQL_SERVERS[0].check_running():
                tests.MYSQL_SERVERS[0].start()
                tests.MYSQL_SERVERS[0].wait_up()

    @unittest.skipIf(sys.version_info < (2, 7, 9), "The support for SSL is "
                     "not available for Python versions < 2.7.9.")
    def test_ssl_connection(self):
        config = {}
        config.update(self.connect_kwargs)

        # Secure by default
        session = mysqlx.get_session(config)

        res = mysqlx.statement.SqlStatement(session._connection,
            "SHOW STATUS LIKE 'Mysqlx_ssl_active'").execute().fetch_all()
        self.assertEqual("ON", res[0][1])

        res = mysqlx.statement.SqlStatement(session._connection,
            "SHOW STATUS LIKE 'Mysqlx_ssl_version'").execute().fetch_all()
        self.assertTrue("TLS" in res[0][1])

        session.close()

        config["ssl-key"] = tests.SSL_KEY
        self.assertRaises(mysqlx.errors.InterfaceError,
                          mysqlx.get_session, config)

        # Connection with ssl parameters
        config["ssl-ca"] = tests.SSL_CA
        config["ssl-cert"] = tests.SSL_CERT

        session = mysqlx.get_session(config)

        res = mysqlx.statement.SqlStatement(session._connection,
            "SHOW STATUS LIKE 'Mysqlx_ssl_active'").execute().fetch_all()
        self.assertEqual("ON", res[0][1])

        res = mysqlx.statement.SqlStatement(session._connection,
            "SHOW STATUS LIKE 'Mysqlx_ssl_version'").execute().fetch_all()
        self.assertTrue("TLS" in res[0][1])

        session.close()

        ssl_ca="{0}{1}".format(config["ssl-ca"][0],
                               quote_plus(config["ssl-ca"][1:]))
        ssl_key="{0}{1}".format(config["ssl-key"][0],
                                quote_plus(config["ssl-key"][1:]))
        ssl_cert="{0}{1}".format(config["ssl-ca"][0],
                                 quote_plus(config["ssl-cert"][1:]))
        uri = build_uri(user=config["user"], password=config["password"],
                        host=config["host"], ssl_ca=ssl_ca,
                        ssl_cert=ssl_cert, ssl_key=ssl_key)
        session = mysqlx.get_session(uri)

        ssl_ca = "({0})".format(config["ssl-ca"])
        ssl_cert = "({0})".format(config["ssl-cert"])
        ssl_key = "({0})".format(config["ssl-key"])
        uri = build_uri(user=config["user"], password=config["password"],
                        host=config["host"], ssl_ca=ssl_ca,
                        ssl_cert=ssl_cert, ssl_key=ssl_key)
        session = mysqlx.get_session(uri)

    def test_disabled_x_protocol(self):
        node_session = mysqlx.get_node_session(self.connect_kwargs)
        res = node_session.sql("SHOW VARIABLES WHERE Variable_name = 'port'") \
                          .execute().fetch_all()
        settings = self.connect_kwargs.copy()
        settings["port"] = res[0][1]  # Lets use the MySQL classic port
        node_session.close()
        self.assertRaises(mysqlx.errors.ProgrammingError, mysqlx.get_session,
                          settings)


@unittest.skipIf(tests.MYSQL_VERSION < (5, 7, 12), "XPlugin not compatible")
class MySQLxNodeSessionTests(tests.MySQLxTests):

    def setUp(self):
        self.connect_kwargs = tests.get_mysqlx_config()
        self.schema_name = self.connect_kwargs["schema"]
        try:
            self.session = mysqlx.get_node_session(self.connect_kwargs)
        except mysqlx.Error as err:
            self.fail("{0}".format(err))

    def test___init__(self):
        bad_config = {
            "host": "bad_host",
            "port": "",
            "username": "root",
            "password": ""
        }
        self.assertRaises(TypeError, mysqlx.NodeSession, bad_config)

    def test_connection_uri(self):
        uri = build_uri(user=self.connect_kwargs["user"],
                        password=self.connect_kwargs["password"],
                        host=self.connect_kwargs["host"],
                        port=self.connect_kwargs["port"],
                        schema=self.connect_kwargs["schema"])
        session = mysqlx.get_node_session(uri)
        self.assertIsInstance(session, mysqlx.NodeSession)

        # Test URI parser function
        for uri, res in _URI_TEST_RESULTS:
            try:
                settings = mysqlx._get_connection_settings(uri)
                self.assertEqual(res, settings)
            except mysqlx.Error:
                self.assertEqual(res, None)

    @unittest.skipIf(tests.MYSQL_VERSION < (5, 7, 15), "--mysqlx-socket option tests not available for this MySQL version")
    def test_mysqlx_socket(self):
        # Connect with unix socket
        uri = "mysqlx://{user}:{password}@({socket})".format(
            user=self.connect_kwargs["user"],
            password=self.connect_kwargs["password"],
            socket=self.connect_kwargs["socket"])

        session = mysqlx.get_session(uri)

    def test_get_schema(self):
        schema = self.session.get_schema(self.schema_name)
        self.assertTrue(schema, mysqlx.Schema)
        self.assertEqual(schema.get_name(), self.schema_name)

    def test_get_default_schema(self):
        schema = self.session.get_default_schema()
        self.assertTrue(schema, mysqlx.Schema)
        self.assertEqual(schema.get_name(), self.connect_kwargs["schema"])

        # Test without default schema configured at connect time
        settings = self.connect_kwargs.copy()
        settings["schema"] = None
        session = mysqlx.get_node_session(settings)
        self.assertRaises(mysqlx.ProgrammingError, session.get_default_schema)
        session.close()

    def test_drop_schema(self):
        test_schema = 'mysql_nodesession_test_drop_schema'
        schema = self.session.create_schema(test_schema)

        self.session.drop_schema(test_schema)
        self.assertFalse(schema.exists_in_database())

    def test_create_schema(self):
        schema = self.session.create_schema(self.schema_name)
        self.assertTrue(schema.exists_in_database())

    def test_sql(self):
        statement = self.session.sql("SELECT VERSION()")
        self.assertTrue(isinstance(statement, mysqlx.statement.Statement))

    def test_rollback(self):
        table_name = "t2"
        schema = self.session.get_schema(self.schema_name)

        if not schema.exists_in_database():
            self.session.create_schema(self.schema_name)

        stmt = "CREATE TABLE {0}.{1}(_id INT)"
        self.session.sql(stmt.format(self.schema_name, table_name)).execute()
        table = schema.get_table(table_name)

        self.session.start_transaction()

        table.insert("_id").values(1).execute()
        self.assertEqual(table.count(), 1)

        self.session.rollback()
        self.assertEqual(table.count(), 0)

        schema.drop_table(table_name)

    def test_commit(self):
        table_name = "t2"
        schema = self.session.get_schema(self.schema_name)

        if not schema.exists_in_database():
            self.session.create_schema(self.schema_name)

        stmt = "CREATE TABLE {0}.{1}(_id INT)"
        self.session.sql(stmt.format(self.schema_name, table_name)).execute()
        table = schema.get_table(table_name)

        self.session.start_transaction()

        table.insert("_id").values(1).execute()
        self.assertEqual(table.count(), 1)

        self.session.commit()
        self.assertEqual(table.count(), 1)

        schema.drop_table(table_name)

    @unittest.skipIf(sys.version_info < (2, 7, 9), "The support for SSL is "
                     "not available for Python versions < 2.7.9.")
    def test_ssl_connection(self):
        config = {}
        config.update(self.connect_kwargs)

        # Secure by default
        session = mysqlx.get_node_session(config)

        res = mysqlx.statement.SqlStatement(session._connection,
            "SHOW STATUS LIKE 'Mysqlx_ssl_active'").execute().fetch_all()
        self.assertEqual("ON", res[0][1])

        res = mysqlx.statement.SqlStatement(session._connection,
            "SHOW STATUS LIKE 'Mysqlx_ssl_version'").execute().fetch_all()
        self.assertTrue("TLS" in res[0][1])

        session.close()

        config["ssl-key"] = tests.SSL_KEY
        self.assertRaises(mysqlx.errors.InterfaceError,
                          mysqlx.get_node_session, config)

        # Connection with ssl parameters
        config["ssl-ca"] = tests.SSL_CA
        config["ssl-cert"] = tests.SSL_CERT

        session = mysqlx.get_node_session(config)

        res = session.sql("SHOW STATUS LIKE 'Mysqlx_ssl_active'") \
                     .execute().fetch_all()
        self.assertEqual("ON", res[0][1])

        res = session.sql("SHOW STATUS LIKE 'Mysqlx_ssl_version'") \
            .execute().fetch_all()
        self.assertTrue("TLS" in res[0][1])

        session.close()

        ssl_ca="{0}{1}".format(config["ssl-ca"][0],
                               quote_plus(config["ssl-ca"][1:]))
        ssl_key="{0}{1}".format(config["ssl-key"][0],
                                quote_plus(config["ssl-key"][1:]))
        ssl_cert="{0}{1}".format(config["ssl-ca"][0],
                                 quote_plus(config["ssl-cert"][1:]))
        uri = build_uri(user=config["user"], password=config["password"],
                        host=config["host"], ssl_ca=ssl_ca,
                        ssl_cert=ssl_cert, ssl_key=ssl_key)
        session = mysqlx.get_node_session(uri)

        ssl_ca = "({0})".format(config["ssl-ca"])
        ssl_cert = "({0})".format(config["ssl-cert"])
        ssl_key = "({0})".format(config["ssl-key"])
        uri = build_uri(user=config["user"], password=config["password"],
                        host=config["host"], ssl_ca=ssl_ca,
                        ssl_cert=ssl_cert, ssl_key=ssl_key)
        session = mysqlx.get_node_session(uri)

    def test_disabled_x_protocol(self):
        res = self.session.sql("SHOW VARIABLES WHERE Variable_name = 'port'") \
                          .execute().fetch_all()
        settings = self.connect_kwargs.copy()
        settings["port"] = res[0][1]  # Lets use the MySQL classic port
        self.assertRaises(mysqlx.errors.ProgrammingError,
                          mysqlx.get_node_session, settings)
