from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app, Markup
from flask_login import current_user, login_required
from flask_babel import _, get_locale
from guess_language import guess_language
from app import db
from app.main.forms import EditProfileForm, EmptyForm, PostForm, SearchForm, \
        MessageForm, OpenGsGenericFlaskForm, OpenGsInfodomainForm, OpenGsOrganizationForm, \
        OpenGsCatalogueForm, OpenGsBuildingBlockGroupForm, OpenGsBuildingBlockForm, DeleteForm, OpenGsRequirementForm, OpenGsSystemForm, \
        OpenGsProcAppRelationForm, OpenGsAppSysRelationForm, OpenGsSysNetRelationForm, GsModelDomPreselectForm, GsModelSysQuickselectForm, GsModelAppQuickselectForm, \
        ChecklistItemForm
from app.models import Requirement, User, Post, Message, Notification, \
        Organization, Infodomain, Coreprocess, Application, System, Network, Room, Person, Document, \
        Catalogue, BuildingBlockGroup, BuildingBlock, AssociationProcApp, AssociationAppSys, AssociationSysNet, \
        GsModelDom, ImplementationDecision, GsModelBase, GsModelSys, GsModelApp, Checklist, ChecklistItem
from app.translate import translate
from app.main import bp




@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = str(get_locale())


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        language = guess_language(form.post.data)
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''
        post = Post(body=form.post.data, author=current_user,
                    language=language)
        db.session.add(post)
        db.session.commit()
        flash(_('Your post is now live!'))
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Home'), form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Explore'),
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.user', username=user.username,
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.user', username=user.username,
                       page=posts.prev_num) if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)


@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    user = User.query.filter_by(username=username).first_or_404()
    form = EmptyForm()
    return render_template('user_popup.html', user=user, form=form)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been saved.'))
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'),
                           form=form)


@bp.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot follow yourself!'))
            return redirect(url_for('main.user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(_('You are following %(username)s!', username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot unfollow yourself!'))
            return redirect(url_for('main.user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_('You are not following %(username)s.', username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    return jsonify({'text': translate(request.form['text'],
                                      request.form['source_language'],
                                      request.form['dest_language'])})


@bp.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(g.search_form.q.data, page,
                               current_app.config['POSTS_PER_PAGE'])
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title=_('Search'), posts=posts,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count', user.new_messages())
        db.session.commit()
        flash(_('Your message has been sent.'))
        return redirect(url_for('main.user', username=recipient))
    return render_template('send_message.html', title=_('Send Message'),
                           form=form, recipient=recipient)


@bp.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()).paginate(
            page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None
    return render_template('messages.html', messages=messages.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/export_posts')
@login_required
def export_posts():
    if current_user.get_task_in_progress('export_posts'):
        flash(_('An export task is currently in progress'))
    else:
        current_user.launch_task('export_posts', _('Exporting posts...'))
        db.session.commit()
    return redirect(url_for('main.user', username=current_user.username))


@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])

##
## OpenGS
##
@bp.route('/organizations')
@login_required
def organizations():
    orgs = Organization.query.filter_by(user_id=current_user.get_id()).order_by(Organization.id.asc())
    user_id = current_user.get_id()
    return render_template('itemlist.html', title=_('Organisationen'),
                           items=orgs, user_id=user_id, form_url=url_for('main.add_org'), form_add_entity="Organisation", item_type="organization")


@bp.route('/add_org', methods=['GET', 'POST'])
@login_required
def add_org():
    form = OpenGsOrganizationForm(user_id=current_user.get_id())
    if form.validate_on_submit():
        org = Organization(name=form.name.data, description=form.description.data, user_id = current_user.get_id())
        db.session.add(org)
        db.session.commit()
        flash(_('New organization has been saved.'))
        return redirect(url_for('main.organizations'))
    return render_template('add_generic_item.html', title = 'Organisation hinzufügen', item_name='Organisation', form=form)

@bp.route('/organization/<org_id>')
@login_required
def organization(org_id):
    org = Organization.query.filter_by(id=org_id).first()
    infodomains = Infodomain.query.filter_by(org_id=org_id)
    return render_template('itemlist.html', title=_(org.name),
                           items=infodomains,
                           form_url=url_for('main.add_infodomain'),
                           form_add_entity="Informationsverbund",
                           org_id=org_id,
                           item_type="infodomain")

@bp.route('/add_infodomain', methods=['GET', 'POST'])
@login_required
def add_infodomain():
    form = OpenGsInfodomainForm(org_id=request.form.get('org_id'))
    if request.form.get('org_id'):
        if form.validate_on_submit():
            infodomain = Infodomain(name=form.name.data, description=form.description.data, org_id = form.org_id.data)
            db.session.add(infodomain)
            db.session.commit()
            flash(_('Informationsverbund gespeichert'))
            return redirect(url_for('main.organization', org_id=form.org_id.data))
    else:
        flash(_('Keine Organisation übergeben.'))
    return render_template('add_generic_item.html', title = 'Informationsverbund hinzufügen', item_name='Informationsverbund', form=form)

@bp.route('/organization/<org_id>/infodomains')
@login_required
def infodomains(org_id):
    infodomains = Infodomain.query.filter_by(org_id=org_id)
    return render_template('infodomains.html', title=_('Informationsverbunde'),
                           infodomains=infodomains)

@bp.route('/infodomain/<infodomain_id>')
@login_required
def infodomain(infodomain_id):
    form = EmptyForm()
    infodomain = Infodomain.query.filter_by(id=infodomain_id).first_or_404()
    org = Organization.query.filter_by(id=infodomain.org_id).first_or_404()
    cproc = Coreprocess.query.filter_by(dom_id=infodomain_id).limit(5).all()
    apps = Application.query.filter_by(dom_id=infodomain_id).limit(5).all()
    systems = System.query.filter_by(dom_id=infodomain_id).limit(5).all()
    networks = Network.query.filter_by(dom_id=infodomain_id).limit(5).all()
    rooms = Room.query.filter_by(dom_id=infodomain_id).limit(5).all()
    persons = Person.query.filter_by(dom_id=infodomain_id).limit(5).all()
    documents = Document.query.filter_by(dom_id=infodomain_id).limit(5).all()

    breadcrumbs = [{'link': url_for('main.organization', org_id=org.id), 'title': org.name}]

    return render_template('infodomain.html', title=_('Informationsverbund ' + infodomain.name),
                           breadcrumbs=breadcrumbs,
                           form=form,
                           infodomain=infodomain,
                           org=org,
                           cprocs=cproc,
                           apps=apps,
                           systems=systems,
                           networks=networks,
                           rooms=rooms,
                           persons=persons,
                           documents=documents)

##
## OpenGS - overview + form pages per infodomain
##

### OpenGS Coreprocesses ###

@bp.route('/infodomain/<infodomain_id>/coreprocesses')
@login_required
def coreprocesses(infodomain_id):
    infodomain = Infodomain.query.filter_by(id=infodomain_id).first_or_404()
    org = Organization.query.filter_by(id=infodomain.org_id).first_or_404()

    breadcrumbs = [{'link': url_for('main.organization', org_id=org.id), 'title': org.name}, 
                   {'link': url_for('main.infodomain', infodomain_id=infodomain_id), 'title': infodomain.name}]
                   
    cprocs = Coreprocess.query.filter_by(dom_id=infodomain_id).all()
    return render_template('itemlist.html', title=_('Kernprozesse'),
                           items=cprocs, item_type='coreprocess', form_add_entity="Kernprozess", form_url=url_for('main.add_coreprocess'), dom_id=infodomain_id, breadcrumbs=breadcrumbs)

@bp.route('/add_coreprocess', methods=['GET', 'POST'])
@login_required
def add_coreprocess():
    form = OpenGsGenericFlaskForm(dom_id=request.form.get('dom_id'))
    if request.form.get('dom_id'):
        if form.validate_on_submit():
            coreprocess = Coreprocess(name=form.name.data, description=form.description.data, dom_id = form.dom_id.data)
            db.session.add(coreprocess)
            db.session.commit()
            flash(_('Geschäftsprozess gespeichert'))
            return redirect(url_for('main.infodomain', infodomain_id=form.dom_id.data))
    else:
        flash(_('Kein Informationsverbund übergeben.'))
    return render_template('add_generic_item.html', title = 'Geschäftsprozess hinzufügen', item_name='Geschäftsprozess', form=form)

@bp.route('/coreprocess/<id>', methods=['GET', 'POST'])
@login_required
def coreprocess(id):
    apprelationform = OpenGsProcAppRelationForm()
    apprelationform.coreprocess_id.data=id
    applications = [(c.id, c.name ) for c in Application.query.all()]
    apprelationform.application_id.choices = applications

    if apprelationform.validate_on_submit():
        procapprelation = AssociationProcApp(
            coreprocess_id=apprelationform.coreprocess_id.data,
            application_id=apprelationform.application_id.data,
            relation_type=apprelationform.relation_type.data
        )
        db.session.add(procapprelation)
        db.session.commit()
        flash(_('Anwendung hinzugefügt'), 'success')
        return redirect(url_for('main.coreprocess', id=apprelationform.coreprocess_id.data))

    coreprocess = Coreprocess.query.filter_by(id=id).first_or_404()
    breadcrumbs = [{'link': url_for('main.organization', org_id=coreprocess.dom.organization.id), 'title': coreprocess.dom.organization.name}, 
                {'link': url_for('main.infodomain', infodomain_id=coreprocess.dom_id), 'title': coreprocess.dom.name}]
    return render_template('coreprocess.html', title=_(coreprocess.name),
                           coreprocess=coreprocess, breadcrumbs=breadcrumbs, apprelationform=apprelationform)

### OpenGS Applications ###

@bp.route('/infodomain/<infodomain_id>/applications')
@login_required
def applications(infodomain_id):
    infodomain = Infodomain.query.filter_by(id=infodomain_id).first_or_404()
    org = Organization.query.filter_by(id=infodomain.org_id).first_or_404()

    breadcrumbs = [{'link': url_for('main.organization', org_id=org.id), 'title': org.name}, 
                   {'link': url_for('main.infodomain', infodomain_id=infodomain_id), 'title': infodomain.name}]
                   
    apps = Application.query.filter_by(dom_id=infodomain_id).all()
    return render_template('applications.html', title=_('Anwendungen'),
                           items=apps, item_type='application', form_add_entity="Anwendung", form_url=url_for('main.add_application'), dom_id=infodomain_id, breadcrumbs=breadcrumbs)


@bp.route('/add_application', methods=['GET', 'POST'])
@login_required
def add_application():
    form = OpenGsGenericFlaskForm(dom_id=request.form.get('dom_id'))
    if request.form.get('dom_id'):
        if form.validate_on_submit():
            item = Application(name=form.name.data, description=form.description.data, dom_id = form.dom_id.data)
            db.session.add(item)
            db.session.commit()
            flash(_('Anwendung gespeichert'))
            return redirect(url_for('main.infodomain', infodomain_id=form.dom_id.data))
    else:
        flash(_('Kein Informationsverbund übergeben.'))
    return render_template('add_generic_item.html', title = 'Anwendung hinzufügen', item_name='Anwendungen', form=form)

@bp.route('/application/<id>', methods=['GET', 'POST'])
@login_required
def application(id):
    application = Application.query.filter_by(id=id).first_or_404()
    gsbuildingblocks = GsModelApp.query.filter_by(application_id=id).all()

    # Form to link a System
    sysrelationform = OpenGsAppSysRelationForm()
    sysrelationform.application_id.data=id
    systems = [(c.id, c.name ) for c in System.query.all()]
    sysrelationform.system_id.choices = systems

    if sysrelationform.submit_appsys.data and sysrelationform.validate_on_submit():
        appsysrelation = AssociationAppSys(
            application_id=sysrelationform.application_id.data,
            system_id=sysrelationform.system_id.data,            
            relation_type=sysrelationform.relation_type.data
        )
        db.session.add(appsysrelation)
        db.session.commit()
        flash(_('Anwendung hinzugefügt'), 'success')
        return redirect(url_for('main.application', id=sysrelationform.application_id.data))

    # Form to link a GS buildingblock
    bbrelationform = GsModelAppQuickselectForm()
    buildingblocks = [(c.id, c.name ) for c in BuildingBlock.query.filter_by(is_active=True).join(BuildingBlock.buildingblockgroup).filter(BuildingBlockGroup.shorthand=='APP').all()]
    bbrelationform.buildingblock_id.choices = buildingblocks
    implementation_decisions = [(c.name, c.value) for c in ImplementationDecision]
    bbrelationform.implementation_decision.choices = implementation_decisions
    bbrelationform.implementation_decision.default = 'yes'
    bbrelationform.dom_id.data = application.dom_id
    bbrelationform.application_id.data = application.id

    if bbrelationform.submit_appq.data and bbrelationform.validate_on_submit():
        current_app.logger.info('submit_appq has been called with app_id %s', bbrelationform.application_id.data)
        bbrelation = GsModelApp(
            dom_id=bbrelationform.dom_id.data,
            application_id=bbrelationform.application_id.data,
            bb_id=bbrelationform.buildingblock_id.data,            
            implementation_decision=bbrelationform.implementation_decision.data
        )
        db.session.add(bbrelation)
        db.session.commit()
        flash(_('Baustein verknüpft'), 'success')
        return redirect(url_for('main.application', id=bbrelationform.application_id.data))

    breadcrumbs = [ {'link': url_for('main.organization', org_id=application.dom.organization.id), 'title': application.dom.organization.name},
                    {'link': url_for('main.infodomain', infodomain_id=application.dom.id), 'title': application.dom.name},
                    {'link': url_for('main.applications', infodomain_id=application.dom_id), 'title': "Anwendungen"}]
    return render_template('application.html', title=_(application.name),
                           application=application, breadcrumbs=breadcrumbs, sysrelationform=sysrelationform, bbrelationform=bbrelationform, gsbuildingblocks=gsbuildingblocks)

### OpenGS Systems ###

@bp.route('/infodomain/<infodomain_id>/systems')
@login_required
def systems(infodomain_id):
    infodomain = Infodomain.query.filter_by(id=infodomain_id).first_or_404()
    org = Organization.query.filter_by(id=infodomain.org_id).first_or_404()

    breadcrumbs = [{'link': url_for('main.organization', org_id=org.id), 'title': org.name}, 
                   {'link': url_for('main.infodomain', infodomain_id=infodomain_id), 'title': infodomain.name}]
                   
    systems = System.query.filter_by(dom_id=infodomain_id).all()
    return render_template('systems.html', title=_('Systeme'),
                           items=systems, item_type='system', form_add_entity="IT System", form_url=url_for('main.add_system'), dom_id=infodomain_id, breadcrumbs=breadcrumbs)

@bp.route('/add_system', methods=['GET', 'POST'])
@login_required
def add_system():
    form = OpenGsSystemForm(dom_id=request.form.get('dom_id'))
    if request.form.get('dom_id'):
        if form.validate_on_submit():
            item = System(  name=form.name.data, 
                            description=form.description.data, 
                            dom_id = form.dom_id.data,
                            number = form.number.data)
            db.session.add(item)
            db.session.commit()
            flash(_('System gespeichert'))
            return redirect(url_for('main.infodomain', infodomain_id=form.dom_id.data))
    else:
        flash(_('Kein Informationsverbund übergeben.'))
    return render_template('add_generic_item.html', title = 'System hinzufügen', item_name='System', form=form)

@bp.route('/system/<id>', methods=['GET', 'POST'])
@login_required
def system(id):
    system = System.query.filter_by(id=id).first_or_404()
    gsbuildingblocks = GsModelSys.query.filter_by(system_id=system.id).all()

    # Form to link a network component
    netrelationform = OpenGsSysNetRelationForm()
    netrelationform.system_id.data=id
    networks = [(c.id, c.name ) for c in Network.query.all()]
    netrelationform.network_id.choices = networks

    # Form to link a GS buildingblock
    bbrelationform = GsModelSysQuickselectForm()
    buildingblocks = [(c.id, c.name ) for c in BuildingBlock.query.filter_by(is_active=True).join(BuildingBlock.buildingblockgroup).filter(BuildingBlockGroup.shorthand.in_(('SYS','NET'))).all()]
    bbrelationform.buildingblock_id.choices = buildingblocks
    implementation_decisions = [(c.name, c.value) for c in ImplementationDecision]
    bbrelationform.implementation_decision.choices = implementation_decisions
    bbrelationform.dom_id.data = system.dom_id
    bbrelationform.system_id.data = id

    if netrelationform.submit_sysnet.data and netrelationform.validate_on_submit():
        sysnetrelation = AssociationSysNet(
            system_id=netrelationform.system_id.data,
            network_id=netrelationform.network_id.data,            
            relation_type=netrelationform.relation_type.data
        )
        db.session.add(sysnetrelation)
        db.session.commit()
        flash(_('Anwendung hinzugefügt'), 'success')
        return redirect(url_for('main.system', id=netrelationform.system_id.data))

    if bbrelationform.submit_sysq.data and bbrelationform.validate_on_submit():
        bbrelation = GsModelSys(
            dom_id=bbrelationform.dom_id.data,
            system_id=bbrelationform.system_id.data,
            bb_id=bbrelationform.buildingblock_id.data,            
            implementation_decision=bbrelationform.implementation_decision.data
        )
        db.session.add(bbrelation)
        db.session.commit()
        flash(_('Baustein verknüpft'), 'success')
        return redirect(url_for('main.system', id=bbrelationform.system_id.data))

    breadcrumbs = [ {'link': url_for('main.organization', org_id=system.dom.organization.id), 'title': system.dom.organization.name},
                    {'link': url_for('main.infodomain', infodomain_id=system.dom.id), 'title': system.dom.name},
                    {'link': url_for('main.systems', infodomain_id=system.dom_id), 'title': "Systeme"}]
    return render_template('system.html', title=_(system.name),
                           system=system, breadcrumbs=breadcrumbs, buildingblocks=gsbuildingblocks, netrelationform=netrelationform, bbrelationform=bbrelationform)

### OpenGS Networks ###

@bp.route('/infodomain/<infodomain_id>/networks')
@login_required
def networks(infodomain_id):
    infodomain = Infodomain.query.filter_by(id=infodomain_id).first_or_404()
    org = Organization.query.filter_by(id=infodomain.org_id).first_or_404()

    breadcrumbs = [{'link': url_for('main.organization', org_id=org.id), 'title': org.name}, 
                   {'link': url_for('main.infodomain', infodomain_id=infodomain_id), 'title': infodomain.name}]
                   
    networks = Network.query.filter_by(dom_id=infodomain_id).all()
    return render_template('itemlist.html', title=_('Netzwerk'),
                           items=networks, item_type='network', form_add_entity="Netzwerk", form_url=url_for('main.add_network'), dom_id=infodomain_id, breadcrumbs=breadcrumbs)

@bp.route('/add_network', methods=['GET', 'POST'])
@login_required
def add_network():
    form = OpenGsGenericFlaskForm(dom_id=request.form.get('dom_id'))
    if request.form.get('dom_id'):
        if form.validate_on_submit():
            item = Network(name=form.name.data, description=form.description.data, dom_id = form.dom_id.data)
            db.session.add(item)
            db.session.commit()
            flash(_('Netzwerk gespeichert'))
            return redirect(url_for('main.infodomain', infodomain_id=form.dom_id.data))
    else:
        flash(_('Kein Informationsverbund übergeben.'))
    return render_template('add_generic_item.html', title = 'Netzwerk hinzufügen', item_name='Netzwerk', form=form)

@bp.route('/network/<id>')
@login_required
def network(id):
    item_type = "Netzwerk"
    item = Network.query.filter_by(id=id).first_or_404()
    breadcrumbs = [ {'link': url_for('main.organization', org_id=item.dom.organization.id), 'title': item.dom.organization.name},
                    {'link': url_for('main.infodomain', infodomain_id=item.dom.id), 'title': item.dom.name},
                    {'link': url_for('main.networks', infodomain_id=item.dom_id), 'title': "Netze und Verbindungen"}]
    return render_template('unlinked_dom_item.html', title=_(item.name),
                           item=item, breadcrumbs=breadcrumbs, item_type=item_type)

### OpenGS Rooms ###

@bp.route('/infodomain/<infodomain_id>/rooms')
@login_required
def rooms(infodomain_id):
    infodomain = Infodomain.query.filter_by(id=infodomain_id).first_or_404()
    org = Organization.query.filter_by(id=infodomain.org_id).first_or_404()

    breadcrumbs = [{'link': url_for('main.organization', org_id=org.id), 'title': org.name}, 
                   {'link': url_for('main.infodomain', infodomain_id=infodomain_id), 'title': infodomain.name}]
                   
    rooms = Room.query.filter_by(dom_id=infodomain_id).all()
    return render_template('itemlist.html', title=_('Raum'),
                           items=rooms, item_type='room', form_add_entity="Raum", form_url=url_for('main.add_room'), dom_id=infodomain_id, breadcrumbs=breadcrumbs)

@bp.route('/add_room', methods=['GET', 'POST'])
@login_required
def add_room():
    form = OpenGsGenericFlaskForm(dom_id=request.form.get('dom_id'))
    if request.form.get('dom_id'):
        if form.validate_on_submit():
            item = Room(name=form.name.data, description=form.description.data, dom_id = form.dom_id.data)
            db.session.add(item)
            db.session.commit()
            flash(_('Raum gespeichert'))
            return redirect(url_for('main.infodomain', infodomain_id=form.dom_id.data))
    else:
        flash(_('Kein Informationsverbund übergeben.'))
    return render_template('add_generic_item.html', title = 'Raum hinzufügen', item_name='Raum', form=form)

@bp.route('/room/<id>')
@login_required
def room(id):
    item_type = "Raum"
    item = Room.query.filter_by(id=id).first_or_404()
    breadcrumbs = [ {'link': url_for('main.organization', org_id=item.dom.organization.id), 'title': item.dom.organization.name},
                    {'link': url_for('main.infodomain', infodomain_id=item.dom.id), 'title': item.dom.name},
                    {'link': url_for('main.rooms', infodomain_id=item.dom_id), 'title': "Räume"}]
    return render_template('unlinked_dom_item.html', title=_(item.name),
                           item=item, breadcrumbs=breadcrumbs, item_type=item_type)

### OpenGS Persons ###

@bp.route('/infodomain/<infodomain_id>/persons')
@login_required
def persons(infodomain_id):
    infodomain = Infodomain.query.filter_by(id=infodomain_id).first_or_404()
    org = Organization.query.filter_by(id=infodomain.org_id).first_or_404()

    breadcrumbs = [{'link': url_for('main.organization', org_id=org.id), 'title': org.name}, 
                   {'link': url_for('main.infodomain', infodomain_id=infodomain_id), 'title': infodomain.name}]
                   
    persons = Person.query.filter_by(dom_id=infodomain_id).all()
    return render_template('itemlist.html', title=_('Person'),
                           items=persons, item_type='person', form_add_entity="Person", form_url=url_for('main.add_person'), dom_id=infodomain_id, breadcrumbs=breadcrumbs)

@bp.route('/add_person', methods=['GET', 'POST'])
@login_required
def add_person():
    form = OpenGsGenericFlaskForm(dom_id=request.form.get('dom_id'))
    if request.form.get('dom_id'):
        if form.validate_on_submit():
            item = Person(name=form.name.data, description=form.description.data, dom_id = form.dom_id.data)
            db.session.add(item)
            db.session.commit()
            flash(_('Person gespeichert'))
            return redirect(url_for('main.infodomain', infodomain_id=form.dom_id.data))
    else:
        flash(_('Kein Informationsverbund übergeben.'))
    return render_template('add_generic_item.html', title = 'Person hinzufügen', item_name='Person', form=form)

@bp.route('/person/<id>')
@login_required
def person(id):
    item_type = "Person"
    item = Person.query.filter_by(id=id).first_or_404()
    breadcrumbs = [ {'link': url_for('main.organization', org_id=item.dom.organization.id), 'title': item.dom.organization.name},
                    {'link': url_for('main.infodomain', infodomain_id=item.dom.id), 'title': item.dom.name},
                    {'link': url_for('main.persons', infodomain_id=item.dom_id), 'title': "Personen"}]
    return render_template('unlinked_dom_item.html', title=_(item.name),
                           item=item, breadcrumbs=breadcrumbs, item_type=item_type)

### OpenGS Documents ###

@bp.route('/infodomain/<infodomain_id>/documents')
@login_required
def documents(infodomain_id):
    infodomain = Infodomain.query.filter_by(id=infodomain_id).first_or_404()
    org = Organization.query.filter_by(id=infodomain.org_id).first_or_404()

    breadcrumbs = [{'link': url_for('main.organization', org_id=org.id), 'title': org.name}, 
                   {'link': url_for('main.infodomain', infodomain_id=infodomain_id), 'title': infodomain.name}]
                   
    documents = Document.query.filter_by(dom_id=infodomain_id).all()
    return render_template('itemlist.html', title=_('Dokument'),
                           items=documents, item_type='document', form_add_entity="Dokument", form_url=url_for('main.add_document'), dom_id=infodomain_id, breadcrumbs=breadcrumbs)

@bp.route('/add_document', methods=['GET', 'POST'])
@login_required
def add_document():
    form = OpenGsGenericFlaskForm(dom_id=request.form.get('dom_id'))
    if request.form.get('dom_id'):
        if form.validate_on_submit():
            item = Document(name=form.name.data, description=form.description.data, dom_id = form.dom_id.data)
            db.session.add(item)
            db.session.commit()
            flash(_('Dokument gespeichert'))
            return redirect(url_for('main.infodomain', infodomain_id=form.dom_id.data))
    else:
        flash(_('Kein Informationsverbund übergeben.'))
    return render_template('add_generic_item.html', title = 'Dokument hinzufügen', item_name='Dokument', form=form)

@bp.route('/document/<id>')
@login_required
def document(id):
    item_type = "Dokument"
    item = Document.query.filter_by(id=id).first_or_404()
    breadcrumbs = [ {'link': url_for('main.organization', org_id=item.dom.organization.id), 'title': item.dom.organization.name},
                    {'link': url_for('main.infodomain', infodomain_id=item.dom.id), 'title': item.dom.name},
                    {'link': url_for('main.documents', infodomain_id=item.dom_id), 'title': "Dokumente"}]
    return render_template('unlinked_dom_item.html', title=_(item.name),
                           item=item, breadcrumbs=breadcrumbs, item_type=item_type)

##
## BSI Grundschutz Kompendium
##

@bp.route('/catalogues')
@login_required
def catalogues():
    catalogues = Catalogue.query.all()
    bbgroups = BuildingBlockGroup.query.all()
    return render_template('catalogues.html', catalogues=catalogues, bbgroups=bbgroups)

@bp.route('/add_catalogue', methods=['GET', 'POST'])
def add_catalogue():
    form = OpenGsCatalogueForm()

    if form.validate_on_submit():
       catalogue = Catalogue(name=form.name.data)
       db.session.add(catalogue)
       db.session.commit()
       flash('New Catalogue has been added')
       return redirect(url_for('main.catalogues'))

    return render_template('add_generic_item.html', form=form, item_name="Katalog")

@bp.route('/add_bbgroup', methods=['GET', 'POST'])
def add_buildingblockgroup():
    form = OpenGsBuildingBlockGroupForm()
    catalogues = [(c.id, c.name) for c in Catalogue.query.all()]
    form.catalogue_id.choices = catalogues

    if form.validate_on_submit():
        bbgroup = BuildingBlockGroup(
            name=form.name.data,
            catalogue_id=form.catalogue_id.data,
            shorthand=form.shorthand.data,
            description=form.description.data)
        db.session.add(bbgroup)
        db.session.commit()
        flash('New Group has been added', 'success')
        return redirect(url_for('main.catalogues'))

    return render_template('add_generic_item.html', form=form, item_name="Bausteingruppe")

@bp.route('/bbgroup/<id>')
@login_required
def buildingblockgroup(id):
    bbdelform = DeleteForm()
    bbdelform.next.data=url_for('main.buildingblockgroup', id=id)
    bbgroup = BuildingBlockGroup.query.filter_by(id=id).first_or_404()
    buildingblocks = BuildingBlock.query.filter_by(buildingblockgroup_id=id).order_by(BuildingBlock.order.asc()).all()
    return render_template('bbgroup.html', bbgroup=bbgroup, buildingblocks=buildingblocks, bbdelform=bbdelform)

@bp.route('/add_buildingblock', methods=['GET', 'POST'])
@login_required
def add_buildingblock():
    form = OpenGsBuildingBlockForm()
    buildingblockgroups = [(c.id, c.name) for c in BuildingBlockGroup.query.all()]
    form.buildingblockgroup_id.choices = buildingblockgroups

    if request.args.get('bbgid'):
        buildingblockgroup_id = request.args.get('bbgid', None, type=int)
        form.buildingblockgroup_id.data = buildingblockgroup_id

    if form.validate_on_submit():
        buildingblock = BuildingBlock(
            name=form.name.data,
            buildingblockgroup_id=form.buildingblockgroup_id.data,
            description=form.description.data,
            prio=form.prio.data,
            order=form.order.data)
        db.session.add(buildingblock)
        db.session.commit()
        flash(Markup('Neuer Baustein <b><i>' + form.name.data + '</i></b> hinzugefügt'), 'success')
        return redirect(url_for('main.buildingblockgroup', id=form.buildingblockgroup_id.data))

    return render_template('add_generic_item.html', form=form, item_name="Baustein")

@bp.route('/del_buildingblock/<id>', methods=['POST'])
@login_required
def del_buildingblock(id):
    form = DeleteForm()
    if form.validate_on_submit():
        next_url = request.form.get("next")
        buildingblock = BuildingBlock.query.filter_by(id=id).first_or_404()
        db.session.delete(buildingblock)
        db.session.commit()

        flash(Markup('Baustein <b><i>' + buildingblock.name + '</i></b> gelöscht'), 'success')
    else:
        flash('Fehler!','danger')
        return render_template('errorpage.html', errors=form.errors), 400

    if next_url:
        return redirect(next_url)
    else:
        return render_template('errorpage.html', errors=form.errors, next_url=next_url), 400
        #return redirect(url_for('main.catalogues'))

@bp.route('/buildingblock/<id>')
@login_required
def buildingblock(id):
    buildingblock = BuildingBlock.query.filter_by(id=id).first_or_404()
    bbgroup = BuildingBlockGroup.query.filter_by(id=buildingblock.buildingblockgroup_id).first_or_404()
    requirements = Requirement.query.filter_by(buildingblock_id=id).all()
    return render_template('buildingblock.html', buildingblock=buildingblock, bbgroup=bbgroup, requirements=requirements)

@bp.route('/add_requirement', methods=['GET', 'POST'])
@login_required
def add_requirement():
    form = OpenGsRequirementForm()

    buildingblocks = [(c.id, c.buildingblockgroup.shorthand + "." + c.order + " " + c.name ) for c in BuildingBlock.query.all()]
    form.buildingblock_id.choices = buildingblocks

    if request.args.get('bbid'):
        buildingblock_id = request.args.get('bbid', None, type=int)
        form.buildingblock_id.data = buildingblock_id

    if form.validate_on_submit():
        requirement = Requirement(
            name=form.name.data,
            protection_level=form.protection_level.data,
            description=form.description.data,
            buildingblock_id=form.buildingblock_id.data,
            order=form.order.data)
        db.session.add(requirement)
        db.session.commit()
        flash(Markup('Neue Anforderung <b><i>' + form.name.data + '</i></b> hinzugefügt'), 'success')
        return redirect(url_for('main.buildingblock', id=form.buildingblock_id.data))

    return render_template('add_generic_item.html', form=form, item_name="Anforderung")

@bp.route('/infodomain/<id>/model_proc', methods=['GET', 'POST'])
@login_required
def model_infodomain(id):
    infodomain = Infodomain.query.filter_by(id=id).first_or_404()
    gsmodeldom = GsModelDom.query.filter_by(dom_id=id).all()
    
    form = GsModelDomPreselectForm()
    implementation_decisions = [(c.name, c.value) for c in ImplementationDecision]
    form.implementation_decision.choices = implementation_decisions
    form.dom_id.value = infodomain.id

    # TODO: Template new_model_form ist eher für (manuelle oder nachträgliche) Bearbeitung, stattdessen heir lieber auf create_basemodel(id) redirecten.
    # Dort dann Dialog, ob man automatisch oder manuell möchte. Manuell = Bearbeitung
    # buildingblocks = BuildingBlock.query.filter_by(is_active=True).join(BuildingBlock.buildingblockgroup).filter(BuildingBlockGroup.shorthand.in_(('ISMS','ORP','CON', 'OPS', 'DER'))).all()
    # return render_template('new_model_form.html', title = 'Neue Modellierung', infodomain=infodomain, buildingblocks=buildingblocks, gsmodeldom=gsmodeldom, form=form)
    if gsmodeldom is None or len (gsmodeldom) == 0:
        return redirect(url_for('main.create_basemodel', id=infodomain.id))

    return render_template('model_proc.html', title="GS Model Prozesse", infodomain=infodomain, gsmodel=gsmodeldom)

@bp.route('/infodomain/<id>/model/create_base', methods=['GET', 'POST'])
@login_required
def create_basemodel(id):

    dom_id=id

    if request.form.get('confirm'):
        base_dom_buildingblocks = [
            16,17,18,19,20,21,
            22,23,24,25,26,27,
            30,31,32,33,34,35,38,
            42,43,44,48,49,
        ]

        for x in base_dom_buildingblocks:
            basemodel = GsModelDom(
                dom_id=id,
                bb_id=x,
            )
            db.session.add(basemodel)
        db.session.commit()
        return redirect(url_for('main.model_infodomain', id=dom_id))

    return render_template('attach_basemodel.html', dom_id=dom_id)

@bp.route('/infodomain/<id>/model_sys')
@login_required
def model_systems(id):
    # TODO: Doppelte Einträge entfernen
    # z.B. hiermit: testdataapp = GsModelApp.query.with_entities(GsModelApp, BuildingBlock).join(BuildingBlock, GsModelApp.bb_id == BuildingBlock.id, isouter=True).all()
    infodomain = Infodomain.query.filter_by(id=id).first_or_404()
    gsmodel = GsModelBase.query.filter_by(dom_id=id).all()

    return render_template('model_sys.html', title="GS Model Systeme", infodomain=infodomain, gsmodel=gsmodel)

@bp.route('/infodomain/<dom_id>/checklists')
@login_required
def dom_checklists(dom_id):
    infodomain = Infodomain.query.filter_by(id=dom_id).first_or_404()

    if request.args.get('prio') == "R3":
        prio = 'R3'
    elif request.args.get('prio') == "R2":
        prio = 'R2'
    else:
        prio = 'R1'

    itemcounter_base_subquery = db.session.query(ChecklistItem.checklist_id, db.func.count(Requirement.protection_level).label('base_count')) \
        .filter(Requirement.protection_level=='BASE')\
        .outerjoin(Requirement, ChecklistItem.requirement_id==Requirement.id) \
        .group_by(ChecklistItem.checklist_id)\
        .subquery()

    itemcounter_standard_subquery = db.session.query(ChecklistItem.checklist_id, db.func.count(Requirement.protection_level).label('standard_count')) \
        .filter(Requirement.protection_level=='STANDARD')\
        .outerjoin(Requirement, ChecklistItem.requirement_id==Requirement.id) \
        .group_by(ChecklistItem.checklist_id)\
        .subquery()

    itemcounter_high_subquery = db.session.query(ChecklistItem.checklist_id, db.func.count(Requirement.protection_level).label('high_count')) \
        .filter(Requirement.protection_level=='HIGH')\
        .outerjoin(Requirement, ChecklistItem.requirement_id==Requirement.id) \
        .group_by(ChecklistItem.checklist_id)\
        .subquery()

    prio_subquery = db.session.query(GsModelBase.id, BuildingBlock.prio.name) \
        .outerjoin(BuildingBlock, GsModelBase.bb_id==BuildingBlock.id) \
        .subquery()

    checklists = db.session.query(Checklist.id, Checklist.name, itemcounter_base_subquery.c.base_count, itemcounter_standard_subquery.c.standard_count, itemcounter_high_subquery.c.high_count, prio_subquery.c.prio)\
        .filter_by(infodomain_id=infodomain.id)\
        .outerjoin(itemcounter_base_subquery, Checklist.id == itemcounter_base_subquery.c.checklist_id) \
        .outerjoin(itemcounter_standard_subquery, Checklist.id == itemcounter_standard_subquery.c.checklist_id) \
        .outerjoin(itemcounter_high_subquery, Checklist.id == itemcounter_high_subquery.c.checklist_id) \
        .outerjoin(prio_subquery, Checklist.gsmodelbase_id == prio_subquery.c.id).filter_by(prio=prio) \
        .all()

    if checklists is None or len (checklists) == 0:
        return redirect(url_for('main.create_checklists', dom_id=infodomain.id))

    return render_template('checklists.html', title="Checklisten", infodomain=infodomain, checklists=checklists, prio=prio)

@bp.route('/infodomain/<dom_id>/create_checklists', methods=['GET', 'POST'])
@login_required
def create_checklists(dom_id):
    infodomain = Infodomain.query.filter_by(id=dom_id).first_or_404()

    if request.form.get('confirm'):
        gsmodelbase = GsModelBase.query.filter_by(dom_id=infodomain.id).all()

        for model in gsmodelbase:
            checklist = Checklist(
                infodomain_id = infodomain.id,
                gsmodelbase_id = model.id,
                name = model.buildingblock.buildingblockgroup.shorthand + '.' + model.buildingblock.order + ' ' + model.buildingblock.name,
                created_by = current_user.id
            )
            db.session.add(checklist)
        db.session.commit()
        return redirect(url_for('main.dom_checklists', dom_id=infodomain.id))

    return render_template('confirm_create_checklists.html', title="Checklisten anlegen", dom_id=dom_id)

@bp.route('/checklist/<checklist_id>/autocreate_checklistitems', methods=['GET', 'POST'])
@login_required
def autocreate_checklistitems(checklist_id):
    checklist = Checklist.query.filter_by(id=checklist_id).first_or_404()

    if request.form.get('confirm'):

        requirements = Requirement.query.filter_by(buildingblock_id=checklist.gsmodelbase.bb_id).all()

        for requirement in requirements:
            checklistitem = ChecklistItem(
                    checklist_id = checklist.id,
                    requirement_id = requirement.id,
                    implementation_decision = "YES",
                    implementation_status = "OPEN"
            )
            db.session.add(checklistitem)
        db.session.commit()
        return redirect(url_for('main.dom_checklists', dom_id=checklist.infodomain_id))

    return render_template('confirm_create_checklistitems.html', title="Checklist befüllen", checklist_id=checklist_id)

@bp.route('/checklist/<checklist_id>')
@login_required
def checklist(checklist_id):
    checklist = Checklist.query.filter_by(id=checklist_id).first_or_404()

    checklist.infodomain.org_id

    breadcrumbs = [{'link': url_for('main.organization', org_id=checklist.infodomain.org_id), 'title': checklist.infodomain.organization.name}, 
                {'link': url_for('main.infodomain', infodomain_id=checklist.infodomain_id), 'title': checklist.infodomain.name},
                {'link': url_for('main.dom_checklists', dom_id=checklist.infodomain_id), 'title': 'Checklisten'}]

    form = ChecklistItemForm()
    return render_template('checklist.html', title="Checkliste "+checklist.name, breadcrumbs=breadcrumbs, checklist=checklist, form=form)

@bp.route('/checklistitem/<checklistitem_id>', methods=['GET', 'POST'])
@login_required
def checklistitem(checklistitem_id):
    checklistitem = ChecklistItem.query.filter_by(id=checklistitem_id).one()
    form = ChecklistItemForm(obj=checklistitem)

    if form.validate_on_submit():
        if form.est_amount.data == "":
            form.est_amount.data = None

        if form.target_date.data == "":
            form.target_date.data = None

        form.populate_obj(checklistitem)
        db.session.add(checklistitem)

        db.session.commit()
        flash(Markup('Eintrag gespeichert'), 'success')
    
    for error in form.errors:
        current_app.logger.info(error)

    return redirect(url_for('main.checklist', checklist_id=checklistitem.checklist_id))