# Security policy

## Reporting a vulnerability

Please don't open a public issue. Report it privately through GitHub instead:
go to the [Security tab](https://github.com/bensynapse/jsonrpcserver/security)
and click "Report a vulnerability". Only the maintainers can see the report.

Include the version, a short description and, if you can, code that shows the
problem. We'll reply within a week.

## Supported versions

| Version | Gets fixes |
|---|---|
| 6.x | Yes, once 6.0.0 is out. Until then, its release candidates get fixes. |
| 5.x | Yes, until 6.0.0 is out. Then security fixes for 12 months. |
| 4.x and older | No |

Until 6.0.0 is released, 5.x is the supported line. Fixes go into the latest
5.x release, and into the next 6.0 release candidate.

Once 6.0.0 is out, fixes go into the latest 6.x release. 5.x keeps getting
security fixes in a new 5.x release for 12 months after the 6.0.0 release
date. Other 5.x bug fixes are at our discretion. Only the latest release of
each line gets fixes, so upgrade within the line first.

Versions 5.0.0 to 5.0.9 send the message of any uncaught exception in a
method to the client. 5.0.10 fixes this, so please upgrade. If you can't yet,
the
[security notes](https://bensynapse.github.io/jsonrpcserver/security/#if-you-are-on-509)
in the docs show how to protect a 5.0.9 server. They also cover the other
settings to check before exposing a server.

## Old domains

jsonrpcserver no longer controls its old website domains. The only official
places are this repository, https://bensynapse.github.io/jsonrpcserver/ and
https://pypi.org/project/jsonrpcserver/.
