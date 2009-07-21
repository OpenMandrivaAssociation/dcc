%define build_sendmail 1
# commandline overrides:
# rpm -ba|--rebuild --with 'xxx'
%{?_without_sendmail: %{expand: %%define build_sendmail 0}}

Summary:	Distributed Checksum Clearinghouse, anti-spam tool
Name:		dcc
Version:	1.3.113
Release:	%mkrel 1
License:	BSD-like
Group:		System/Servers
URL:		http://www.rhyolite.com/anti-spam/dcc/
Source0:	http://www.rhyolite.com/dcc/source/dcc.tar.Z
Patch0:		dcc-dccd-initscript.diff
Requires(post): rpm-helper perl rrdtool
Requires(preun): rpm-helper perl rrdtool
Requires(pre): rpm-helper
Requires(postun): rpm-helper
Requires:	perl rrdtool
BuildRequires:	perl wget apache-base
%if %{build_sendmail}
BuildRequires:	sendmail-devel
%endif
BuildRoot:	%{_tmppath}/%{name}-%{version}-buildroot

%description
Distributed Checksum Clearinghouse or DCC is a cooperative,
distributed system intended to detect "bulk" mail or mail sent to
many people. It allows individuals receiving a single mail message
to determine that many other people have been sent essentially
identical copies of the message and so reject the message. It can
identify some unsolicited bulk mail using "spam traps" and other
detectors, but that is not its focus.

The DCC can be viewed as a tool for end users to enforce their
right to "opt-in" to streams of bulk mail by refusing all bulk mail
except from sources in a "white list."  White lists are generally
the responsibility of DCC clients, since only they know which bulk
mail they solicited.

NB to use DCC to reject SPAM you need to configure
%{_datadir}/dcc/dcc_conf and either use procmail or sendmail to
feed the messages to DCC

%package	cgi
Summary:	The cgi-scripts for managing mail delivery on a DCC enabled server
Group:		System/Servers
Requires:	apache-mpm-prefork
Requires:	%{name} = %{version}

%description	cgi
Example set of cgi-scripts to allow users to point-and-click
manage their own DCC whitelists and thus what is delivered to
them.  Allows overriding of site level lists.  The scripts give
controlled access to the whitelists which are otherwise in
protected directory space (owned by dcc).

NB these scripts need configured after installation

%if %{build_sendmail}
%package	sendmail
Summary:	Distributed Checksum Clearinghouse Milter Interface
Group:		System/Servers
Requires:	sendmail
Requires:	sendmail-cf
Requires:	%{name} = %{version}

%description	sendmail
Dccm is a daemon built with the sendmail milter interface intended
to connect sendmail to DCC servers.
%endif

%package	devel
Summary:	Development headers and libraries for %{name}
Group:		Development/C

%description	devel
Development headers and libraries for %{name}

%prep

%setup -q -n %{name}-%{version}
%patch0 -p0 -b .initscript

# fix defaults
find . -type f | xargs perl -pi -e "s|/usr/local|%{_prefix}|g"
find . -type f | xargs perl -pi -e "s|/var/dcc|%{_localstatedir}/lib/dcc|g"

# lib64 fixes
perl -pi -e "s|/usr/lib|%{_libdir}|g" configure

%build

./configure \
    --libexecdir=%{_sbindir} \
%if %{build_sendmail}
    --with-sendmail \
    --with-dccm \
%else
    --disable-dccm \
%endif
    --with-installroot=%{buildroot} \
    --homedir=%{_localstatedir}/lib/dcc \
    --bindir=%{_bindir} \
    --mandir=%{_mandir} \
    --with-DCC-MD5 \
    --disable-sys-inst \
    --with-uid=dcc \
    --with-cgibin=/var/www/dcc-bin \
    --with-rundir=/var/run/dcc \
    --with-db-memory=32 

#    --prefix=%{_localstatedir}/lib/dcc \
			  
perl -p -i -e "s:\".*\":\"%{_sbindir}\": if m/define\s+DCC_LIBEXECDIR/ ;" include/dcc_config.h

make CWARN="%{optflags}"

# make extras
make CWARN="%{optflags}" -C dccifd/dccif-test

%install
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}

# don't fiddle with the initscript!
export DONT_GPRINTIFY=1

install -d %{buildroot}%{_initrddir}
install -d %{buildroot}%{_sysconfdir}/cron.daily
install -d %{buildroot}%{_sysconfdir}/httpd/webapps.d
install -d %{buildroot}/var/run/dcc
install -d %{buildroot}%{_localstatedir}/lib/dcc/{log,userdirs/{local,esmtp,cyrus,procmail}}
install -d %{buildroot}%{_mandir}/man8
install -d %{buildroot}%{_libdir}
install -d %{buildroot}%{_includedir}/dcc

export INST_UID="`id -u`"
export INST_GID="`id -g`"

make MANOWN=$INST_UID MANGRP=$INST_GID DCC_SUID=$INST_UID DCC_OWN=$INST_UID \
    DCC_GRP=$INST_GID BINOWN=$INST_UID GRP=$INST_GID INSTALL="install -c" \
    install

chmod 755 %{buildroot}%{_sbindir}/* %{buildroot}%{_bindir}/* 

install -m0755 misc/cron-dccd %{buildroot}%{_sysconfdir}/cron.daily/dccd
install -m0755 misc/rcDCC %{buildroot}%{_initrddir}/dccd
install -m0600 homedir/flod %{buildroot}%{_localstatedir}/lib/dcc/flod

install -m0755 dccifd/dccif-test/dccif-test %{buildroot}%{_sbindir}/
install -m0755 dccifd/dccif-test/dccif-test.pl %{buildroot}%{_sbindir}/
install -m0755 dccifd/dccif.pl %{buildroot}%{_sbindir}/

%if %{build_sendmail}
install -d %{buildroot}%{_datadir}/sendmail-cf/feature
install -m0644 misc/dcc.m4 %{buildroot}%{_datadir}/sendmail-cf/feature/
install -m0644 misc/dccdnsbl.m4 %{buildroot}%{_datadir}/sendmail-cf/feature/
#install -m0644 misc/dict-attack-aliases %{buildroot}%{_localstatedir}/lib/dcc/
#install -m0755 misc/filter-dict-attack %{buildroot}%{_sbindir}/
%endif

# Set some initial logging, but no rejections
perl -p -i -e "s/BRAND=\$/BRAND=%{version}-%{release}/ ; s/DCCM_LOG_AT=\$/\$&10/ ; " \
	%{buildroot}%{_localstatedir}/lib/dcc/dcc_conf

# install the apache2 config
cat > %{buildroot}%{_sysconfdir}/httpd/webapps.d/dcc.conf <<EOF

ScriptAlias /dcc-bin/ /var/www/dcc-bin/

    <Directory /var/www/dcc-bin/>

	Order deny,allow
	Deny from all
	allow from 127.0.0.1

	SSLCipherSuite ALL:!ADH:RC4+RSA:+HIGH:+MEDIUM:+LOW:+SSLv2:+EXP
	SSLRequireSSL
	ErrorDocument 403 /dcc-bin/http2https

	AuthType Basic
	AuthName "DCC user"
	AuthUserFile %{_localstatedir}/lib/dcc/userdirs/webusers
	require valid-user

    </Directory>
EOF

echo "# put users in here" > %{buildroot}%{_localstatedir}/lib/dcc/userdirs/webusers

# prepare for docs inclusion
cp misc/README README.misc
cp homedir/README README.homedir
cp cgi-bin/README README.cgi-bin

# fix strange attribs
chmod 644 CHANGES LICENSE README* *.txt *.html

# install devel files
install -m0644 dccd/*.h %{buildroot}%{_includedir}/dcc/
install -m0644 dcclib/*.h %{buildroot}%{_includedir}/dcc/
install -m0644 include/*.h %{buildroot}%{_includedir}/dcc/
install -m0644 srvrlib/*.h %{buildroot}%{_includedir}/dcc/
install -m0755 dcclib/libdcc.a %{buildroot}%{_libdir}/
install -m0755 srvrlib/libsrvr.a %{buildroot}%{_libdir}/
install -m0755 thrlib/libthr.a %{buildroot}%{_libdir}/

# house cleaning
rm -f %{buildroot}/var/www/dcc-bin/README
rm -f %{buildroot}%{_sbindir}/rcDCC
rm -f %{buildroot}%{_sbindir}/cron-dccd
rm -f %{buildroot}%{_sbindir}/logger
rm -f %{buildroot}%{_sbindir}/updatedcc
rm -f %{buildroot}%{_sbindir}/uninstalldcc

# install man pages
install -m0644 *.8 %{buildroot}%{_mandir}/man8/

%pre
%_pre_useradd dcc %{_localstatedir}/lib/dcc /bin/sh

%post
%_post_service dccd
# this causes a hang if not connected to the internet
# deactivate it for now... user should read man pages
# instead...
#%{_bindir}/cdcc info > %{_localstatedir}/lib/dcc/map.txt || :

%preun
%_preun_service dccd

%postun
%_postun_userdel dcc

%clean
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}

%files
%defattr(-,root,root)
%doc CHANGES FAQ.txt INSTALL.txt LICENSE README.misc README.homedir
%doc FAQ.html INSTALL.html cdcc.html dbclean.html dblist.html
%doc dcc.html dccd.html dccifd.html dccproc.html dccsight.html

%attr(0755,root,root) %{_sysconfdir}/cron.daily/dccd
%attr(0755,root,root) %{_initrddir}/dccd

%config(noreplace) %attr(0600,dcc,dcc) %{_localstatedir}/lib/dcc/ids
%config(noreplace) %attr(0600,dcc,dcc) %{_localstatedir}/lib/dcc/map
%config(noreplace) %attr(0600,dcc,dcc) %{_localstatedir}/lib/dcc/map.txt
%config(noreplace) %attr(0644,dcc,dcc) %{_localstatedir}/lib/dcc/dcc_conf
#%config(noreplace) %attr(0644,dcc,dcc) %{_localstatedir}/lib/dcc/dcc_db
#%config(noreplace) %attr(0644,dcc,dcc) %{_localstatedir}/lib/dcc/dcc_db.hash
%config(noreplace) %attr(0644,dcc,dcc) %{_localstatedir}/lib/dcc/flod
%config(noreplace) %attr(0644,dcc,dcc) %{_localstatedir}/lib/dcc/whiteclnt
%config(noreplace) %attr(0644,dcc,dcc) %{_localstatedir}/lib/dcc/whitecommon
%config(noreplace) %attr(0644,dcc,dcc) %{_localstatedir}/lib/dcc/whitelist
%config(noreplace) %attr(0644,dcc,dcc) %{_localstatedir}/lib/dcc/grey_flod
%config(noreplace) %attr(0644,dcc,dcc) %{_localstatedir}/lib/dcc/grey_whitelist

%attr(4755,root,root) %{_bindir}/cdcc
%attr(4755,root,root) %{_bindir}/dccproc
%attr(0755,root,root) %{_bindir}/dccif-test

%attr(0755,root,root) %{_sbindir}/dbclean
%attr(0755,root,root) %{_sbindir}/dblist
%attr(0755,root,root) %{_sbindir}/dccd
%attr(0755,root,root) %{_sbindir}/dccifd
%attr(0755,root,root) %{_sbindir}/newwebuser
#%attr(0755,root,root) %{_sbindir}/refeed
%attr(0755,root,root) %{_sbindir}/start-dccd
%attr(0755,root,root) %{_sbindir}/start-dccifd
%attr(0755,root,root) %{_sbindir}/stop-dccd
%attr(0755,root,root) %{_sbindir}/wlist
%attr(4755,root,root) %{_sbindir}/dccsight
%attr(0755,root,root) %{_sbindir}/start-grey
%attr(0755,root,root) %{_sbindir}/fetchblack
%attr(0755,root,root) %{_sbindir}/list-clients
%attr(0755,root,root) %{_sbindir}/dns-helper

# rrdtool stuff
%attr(0755,root,root) %{_sbindir}/dcc-stats-collect
%attr(0755,root,root) %{_sbindir}/dcc-stats-graph
%attr(0755,root,root) %{_sbindir}/dcc-stats-init
%attr(0755,root,root) %{_sbindir}/stats-get

# extras
%attr(0755,root,root) %{_sbindir}/dccif-test
%attr(0755,root,root) %{_sbindir}/dccif-test.pl
%attr(0755,root,root) %{_sbindir}/dccif.pl
%attr(0755,root,root) %{_sbindir}/fetch-testmsg-whitelist

%attr(0755,dcc,dcc) %dir %{_localstatedir}/lib/dcc
%attr(0755,dcc,dcc) %dir %{_localstatedir}/lib/dcc/log
%attr(0755,dcc,dcc) %dir %{_localstatedir}/lib/dcc/userdirs
%attr(0755,dcc,dcc) %dir %{_localstatedir}/lib/dcc/userdirs/local
%attr(0755,dcc,dcc) %dir %{_localstatedir}/lib/dcc/userdirs/cyrus
%attr(0755,dcc,dcc) %dir %{_localstatedir}/lib/dcc/userdirs/procmail
%attr(0755,dcc,dcc) %dir %{_localstatedir}/lib/dcc/userdirs/esmtp
%attr(0755,dcc,dcc) %dir /var/run/dcc

%attr(0644,root,root) %{_mandir}/man8/cdcc.8*
%attr(0644,root,root) %{_mandir}/man8/dbclean.8*
%attr(0644,root,root) %{_mandir}/man8/dblist.8*
%attr(0644,root,root) %{_mandir}/man8/dcc.8*
%attr(0644,root,root) %{_mandir}/man8/dccd.8*
%attr(0644,root,root) %{_mandir}/man8/dccifd.8*
%attr(0644,root,root) %{_mandir}/man8/dccproc.8*
%attr(0644,root,root) %{_mandir}/man8/dccsight.8*
#%attr(0644,root,root) %{_mandir}/man8/dnsbl.8*

# excludes - files related to dcc-sendmail
%exclude %{_sbindir}/hackmc
%exclude %{_sbindir}/start-dccm
%exclude %{_mandir}/man8/dccm.8*

%if %{build_sendmail}
%files sendmail
%defattr(-,root,root)
%doc dccm.html
#%config(noreplace) %attr(0644,dcc,dcc) %{_localstatedir}/lib/dcc/dict-attack-aliases
%attr(0755,root,root) %{_sbindir}/dccm
#%attr(0755,root,root) %{_sbindir}/filter-dict-attack
%attr(0755,root,root) %{_sbindir}/hackmc
#%attr(0755,root,root) %{_sbindir}/na-spam
#%attr(0755,root,root) %{_sbindir}/ng-spam
%attr(0755,root,root) %{_sbindir}/start-dccm
%attr(0644,root,root) %{_datadir}/sendmail-cf/feature/dcc.m4
%attr(0644,root,root) %{_datadir}/sendmail-cf/feature/dccdnsbl.m4
%attr(0644,root,root) %{_mandir}/man8/dccm.8*
%endif

%files cgi
%defattr(-,root,root)
%doc README.cgi-bin
%attr(0644,root,root) %config(noreplace) %{_sysconfdir}/httpd/webapps.d/dcc.conf
%attr(0644,root,root) %config(noreplace) %{_localstatedir}/lib/dcc/userdirs/webusers
%attr(0755,root,root) /var/www/dcc-bin/chgpasswd
%attr(0755,root,root) /var/www/dcc-bin/common
%attr(0755,root,root) /var/www/dcc-bin/edit-whiteclnt
%attr(0755,root,root) /var/www/dcc-bin/http2https
%attr(0755,root,root) /var/www/dcc-bin/list-log
%attr(0755,root,root) /var/www/dcc-bin/list-msg
%attr(0755,root,root) /var/www/dcc-bin/webuser-notify
%attr(0755,root,root) /var/www/dcc-bin/footer
%attr(0755,root,root) /var/www/dcc-bin/header

%files devel
%defattr(-,root,root)
%attr(0644,root,root) %{_includedir}/dcc/*.h
%attr(0755,root,root) %{_libdir}/*.a


