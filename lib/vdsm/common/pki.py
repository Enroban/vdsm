# coding=utf-8
# Copyright 2017 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

# 多处都调用了这个，实际是，证书文件等

from __future__ import absolute_import

import os
from . import constants

PKI_DIR = os.path.join(constants.SYSCONF_PATH, 'pki', 'vdsm')
KEY_FILE = os.path.join(PKI_DIR, 'keys', 'vdsmkey.pem')
CERT_FILE = os.path.join(PKI_DIR, 'certs', 'vdsmcert.pem')
CA_FILE = os.path.join(PKI_DIR, 'certs', 'cacert.pem')
