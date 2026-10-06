# Security policy

## Reporting a vulnerability

Please don't open a public issue. Report it privately through GitHub instead:
go to the [Security tab](https://github.com/bensynapse/jsonrpcserver/security)
and click "Report a vulnerability". Only the maintainers can see the report.

Include the version, a short description and, if you can, code that shows the
problem. We'll reply within a week.

## Supported versions

Fixes go into the latest 5.x release. Older releases don't get updates.

Versions before 5.0.10 send the message of any uncaught exception in a method
to the client. Please upgrade when 5.0.10 is on PyPI. Until then, the
[security notes](https://bensynapse.github.io/jsonrpcserver/security/#if-you-are-on-509)
in the docs show how to protect a 5.0.9 server. They also cover the other
settings to check before exposing a server.

## Old domains

jsonrpcserver no longer controls its old website domains. The only official
places are this repository, https://bensynapse.github.io/jsonrpcserver/ and
https://pypi.org/project/jsonrpcserver/.
