import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { I18nContext } from './i18nContext'
import { normalizeLanguage, type AppLanguage } from './language'

export type TranslationKey =
  | 'common.loading'
  | 'common.cancel'
  | 'common.save'
  | 'common.edit'
  | 'common.delete'
  | 'common.actions'
  | 'common.active'
  | 'common.inactive'
  | 'common.suspended'
  | 'common.backHome'
  | 'common.language'
  | 'common.russian'
  | 'common.english'
  | 'common.workspace'
  | 'common.workspaces'
  | 'common.user'
  | 'common.users'
  | 'common.name'
  | 'common.email'
  | 'common.password'
  | 'common.role'
  | 'common.department'
  | 'common.status'
  | 'common.description'
  | 'login.heroTitle'
  | 'login.heroCopy'
  | 'login.signIn'
  | 'login.useAccount'
  | 'login.email'
  | 'login.password'
  | 'login.signingIn'
  | 'login.invalidCredentials'
  | 'nav.home'
  | 'nav.dashboard'
  | 'nav.people'
  | 'nav.work'
  | 'nav.money'
  | 'nav.schedule'
  | 'nav.employeeEvaluations'
  | 'nav.reports'
  | 'nav.settings'
  | 'nav.system'
  | 'nav.workspace'
  | 'nav.aiArchitect'
  | 'nav.admin'
  | 'nav.superadmin'
  | 'nav.searchWorkspace'
  | 'nav.assigned'
  | 'nav.profile'
  | 'nav.newPending'
  | 'nav.requestHistory'
  | 'nav.newTemplate'
  | 'profile.title'
  | 'profile.role'
  | 'profile.workspaceInfo'
  | 'profile.loadingWorkspace'
  | 'profile.department'
  | 'profile.fullName'
  | 'profile.accountStatus'
  | 'profile.editProfile'
  | 'profile.saveChanges'
  | 'profile.updated'
  | 'profile.updateFailed'
  | 'profile.logout'
  | 'admin.title'
  | 'admin.selectWorkspace'
  | 'admin.createUser'
  | 'admin.createNewUser'
  | 'admin.noUsers'
  | 'admin.fullName'
  | 'admin.role'
  | 'admin.accessProfile'
  | 'admin.accessProfiles'
  | 'admin.accessProfileName'
  | 'admin.baseRole'
  | 'admin.tabVisibility'
  | 'admin.fieldVisibility'
  | 'admin.noFormFields'
  | 'admin.noAccessProfile'
  | 'admin.createAccessProfile'
  | 'admin.saveAccessProfile'
  | 'admin.accessProfileCreated'
  | 'admin.accessProfileUpdated'
  | 'admin.accessProfileSaveFailed'
  | 'admin.accessProfileUpdateFailed'
  | 'admin.deleteAccessProfileConfirm'
  | 'admin.roleNameRequired'
  | 'admin.selectWorkspacePlaceholder'
  | 'admin.selectDepartmentPlaceholder'
  | 'admin.unassigned'
  | 'admin.deactivate'
  | 'admin.reactivate'
  | 'admin.userCreated'
  | 'admin.createFailed'
  | 'admin.roleUpdated'
  | 'admin.roleUpdateFailed'
  | 'admin.selfRoleBlocked'
  | 'admin.departmentUpdateFailed'
  | 'admin.statusUpdateFailed'
  | 'admin.departments'
  | 'admin.departmentName'
  | 'admin.descriptionOptional'
  | 'admin.add'
  | 'admin.noDepartments'
  | 'admin.deleteDepartmentConfirm'
  | 'super.title'
  | 'super.subtitle'
  | 'super.aiProvider'
  | 'super.provider'
  | 'super.model'
  | 'super.baseUrl'
  | 'super.apiKey'
  | 'super.saveAiProvider'
  | 'super.aiProviderSaved'
  | 'super.aiProviderFailed'
  | 'super.liveProviderRequirements'
  | 'super.userPasswords'
  | 'super.userPasswordsNote'
  | 'super.newTemporaryPassword'
  | 'super.confirmTemporaryPassword'
  | 'super.loadingUsers'
  | 'super.noUsers'
  | 'super.resetPassword'
  | 'super.resettingPassword'
  | 'super.selectUserFirst'
  | 'super.passwordMismatch'
  | 'super.passwordTooShort'
  | 'super.passwordReset'
  | 'super.passwordResetFailed'
  | 'super.newWorkspace'
  | 'super.activeWorkspaces'
  | 'super.company'
  | 'super.subdomain'
  | 'super.adminContact'
  | 'super.modules'
  | 'super.manageModules'
  | 'super.rename'
  | 'super.suspend'
  | 'super.activate'
  | 'super.launchWorkspace'
  | 'super.companyName'
  | 'super.initialAdmin'
  | 'super.emailAddress'
  | 'super.createWorkspace'
  | 'super.creatingWorkspace'
  | 'super.workspaceCreated'
  | 'super.workspaceCreateFailed'
  | 'super.suspendConfirm'
  | 'super.newWorkspaceName'
  | 'super.workspaceModules'
  | 'super.moduleSaveFailed'
  | 'super.saveModules'
  | 'super.synergies'
  | 'ai.title'
  | 'ai.subtitle'
  | 'ai.conversation'
  | 'ai.emptyPrompt'
  | 'ai.placeholder'
  | 'ai.send'
  | 'ai.thinking'
  | 'ai.generate'
  | 'ai.generating'
  | 'ai.blueprint'
  | 'ai.profile'
  | 'ai.departments'
  | 'ai.roles'
  | 'ai.entities'
  | 'ai.assumptions'
  | 'ai.applied'
  | 'ai.applyProposal'
  | 'ai.appliedArtifacts'
  | 'ai.history'
  | 'ai.noHistory'
  | 'ai.rollback'
  | 'ai.you'
  | 'ai.failedStart'
  | 'ai.failedSend'
  | 'ai.failedGenerate'
  | 'ai.failedApply'
  | 'ai.failedRollback'
  | 'home.welcomeBack'
  | 'home.subtitle'
  | 'home.nextActions'
  | 'home.fastRouting'
  | 'home.workspaceSections'
  | 'home.enabledShell'
  | 'home.ready'
  | 'home.soon'
  | 'home.liveWorkflowData'
  | 'home.installedTemplates'
  | 'home.readyForSetup'
  | 'home.weekEvents'
  | 'home.weekEventsSub'
  | 'home.openSchedule'
  | 'home.noEvents'
  | 'home.noAnimator'
  | 'market.general'
  | 'market.functional'
  | 'market.customers'
  | 'market.peopleDescription'
  | 'market.workDescription'
  | 'market.moneyDescription'
  | 'market.reportsDescription'
  | 'market.settingsDescription'
  | 'market.createRequest'
  | 'market.addCustomer'
  | 'market.openAiArchitect'
  | 'market.openSchedule'
  | 'market.needsAttention'
  | 'market.recentWork'
  | 'market.scheduleConflicts'
  | 'market.openRecords'
  | 'market.openRequests'
  | 'market.openAssignedWork'
  | 'market.departments'
  | 'market.openForms'
  | 'market.openReports'
  | 'market.reportTypes'
  | 'market.openProfile'
  | 'market.adminPanel'
  | 'market.crmModules'
  | 'market.availableNow'
  | 'market.destinations'
  | 'modules.title'
  | 'modules.coreModules'
  | 'modules.loading'
  | 'modules.open'
  | 'modules.noneEnabled'
  | 'modules.back'
  | 'modules.notFound'
  | 'modules.disabled'
  | 'modules.starterTemplates'
  | 'modules.starterKit'
  | 'modules.templatesInstalled'
  | 'modules.installTemplates'
  | 'modules.installing'
  | 'modules.installed'
  | 'modules.installStarterKit'
  | 'modules.installFailed'
  | 'modules.forms'
  | 'modules.reports'
  | 'modules.capabilities'
  | 'modules.pluginTemplates'
  | 'modules.templatesConnected'
  | 'modules.noTemplates'
  | 'modules.connectedCore'
  | 'modules.managedTitle'
  | 'modules.managedDescription'
  | 'modules.openSuperadmin'
  | 'dashboard.openRequests'
  | 'dashboard.viewRequests'
  | 'dashboard.newRequest'
  | 'dashboard.quickRequest'
  | 'dashboard.manageTemplates'
  | 'dashboard.close'
  | 'dashboard.cannotCreate'
  | 'dashboard.noTemplates'
  | 'dashboard.requestSubmitted'
  | 'dashboard.submitFailed'
  | 'forms.noTemplates'
  | 'requests.noTemplates'
  | 'template.registry'
  | 'template.workflow'
  | 'template.form'
  | 'template.report'

const translations: Record<AppLanguage, Record<TranslationKey, string>> = {
  ru: {
    'common.loading': 'Загрузка...',
    'common.cancel': 'Отмена',
    'common.save': 'Сохранить',
    'common.edit': 'Редактировать',
    'common.delete': 'Удалить',
    'common.actions': 'Действия',
    'common.active': 'Активен',
    'common.inactive': 'Неактивен',
    'common.suspended': 'Остановлен',
    'common.backHome': 'Назад на главную',
    'common.language': 'Язык',
    'common.russian': 'Русский',
    'common.english': 'English',
    'common.workspace': 'Рабочая область',
    'common.workspaces': 'Рабочие области',
    'common.user': 'Пользователь',
    'common.users': 'Пользователи',
    'common.name': 'Имя',
    'common.email': 'Email',
    'common.password': 'Пароль',
    'common.role': 'Роль',
    'common.department': 'Отдел',
    'common.status': 'Статус',
    'common.description': 'Описание',
    'login.heroTitle': 'Рабочая среда для событий, команд и клиентских задач.',
    'login.heroCopy': 'Заявки, формы, отчеты, файлы и настройки рабочей области в одном рабочем интерфейсе.',
    'login.signIn': 'Войти',
    'login.useAccount': 'Используйте аккаунт рабочей области.',
    'login.email': 'Email',
    'login.password': 'Пароль',
    'login.signingIn': 'Вход...',
    'login.invalidCredentials': 'Неверный email или пароль',
    'nav.home': 'Главная',
    'nav.dashboard': 'Дашборд',
    'nav.people': 'Клиенты',
    'nav.work': 'Работа',
    'nav.money': 'Финансы',
    'nav.schedule': 'График',
    'nav.employeeEvaluations': 'Оценка сотрудников',
    'nav.reports': 'Отчеты',
    'nav.settings': 'Настройки',
    'nav.system': 'Система',
    'nav.workspace': 'Рабочая область',
    'nav.aiArchitect': 'AI Архитектор',
    'nav.admin': 'Админ',
    'nav.superadmin': 'Суперадмин',
    'nav.searchWorkspace': 'Поиск по рабочей области',
    'nav.assigned': 'Назначено',
    'nav.profile': 'Профиль',
    'nav.newPending': 'новых / в ожидании',
    'nav.requestHistory': 'История заявок',
    'nav.newTemplate': 'Новый шаблон',
    'profile.title': 'Мой профиль',
    'profile.role': 'Роль',
    'profile.workspaceInfo': 'Рабочая область',
    'profile.loadingWorkspace': 'Загрузка рабочей области...',
    'profile.department': 'Отдел',
    'profile.fullName': 'Полное имя',
    'profile.accountStatus': 'Статус аккаунта',
    'profile.editProfile': 'Редактировать профиль',
    'profile.saveChanges': 'Сохранить изменения',
    'profile.updated': 'Профиль обновлен',
    'profile.updateFailed': 'Не удалось обновить профиль',
    'profile.logout': 'Выйти из аккаунта',
    'admin.title': 'Управление пользователями',
    'admin.selectWorkspace': 'Выберите рабочую область:',
    'admin.createUser': 'Создать пользователя',
    'admin.createNewUser': 'Создать пользователя',
    'admin.noUsers': 'В этой рабочей области нет пользователей',
    'admin.fullName': 'Полное имя:',
    'admin.role': 'Роль:',
    'admin.accessProfile': 'Профиль доступа',
    'admin.accessProfiles': 'Профили доступа',
    'admin.accessProfileName': 'Название профиля',
    'admin.baseRole': 'Базовая роль',
    'admin.tabVisibility': 'Видимость вкладок',
    'admin.fieldVisibility': 'Видимость полей форм',
    'admin.noFormFields': 'Поля появятся здесь после создания шаблонов форм.',
    'admin.noAccessProfile': 'Без отдельного профиля',
    'admin.createAccessProfile': 'Создать профиль доступа',
    'admin.saveAccessProfile': 'Сохранить профиль доступа',
    'admin.accessProfileCreated': 'Профиль доступа создан',
    'admin.accessProfileUpdated': 'Профиль доступа обновлен',
    'admin.accessProfileSaveFailed': 'Не удалось сохранить профиль доступа',
    'admin.accessProfileUpdateFailed': 'Не удалось обновить профиль доступа пользователя',
    'admin.deleteAccessProfileConfirm': 'Удалить этот профиль доступа?',
    'admin.roleNameRequired': 'Укажите название профиля доступа',
    'admin.selectWorkspacePlaceholder': '-- Выберите рабочую область --',
    'admin.selectDepartmentPlaceholder': '-- Выберите отдел --',
    'admin.unassigned': '-- Не назначен --',
    'admin.deactivate': 'Отключить',
    'admin.reactivate': 'Включить',
    'admin.userCreated': 'Пользователь создан',
    'admin.createFailed': 'Не удалось создать пользователя',
    'admin.roleUpdated': 'Роль обновлена',
    'admin.roleUpdateFailed': 'Не удалось обновить роль',
    'admin.selfRoleBlocked': 'Нельзя менять собственную роль. Попросите другого администратора.',
    'admin.departmentUpdateFailed': 'Не удалось обновить отдел',
    'admin.statusUpdateFailed': 'Не удалось обновить статус пользователя',
    'admin.departments': 'Отделы',
    'admin.departmentName': 'Название отдела',
    'admin.descriptionOptional': 'Описание (необязательно)',
    'admin.add': 'Добавить',
    'admin.noDepartments': 'Отделы не найдены',
    'admin.deleteDepartmentConfirm': 'Удалить этот отдел?',
    'super.title': 'Центр управления суперадмина',
    'super.subtitle': 'Системное управление рабочими областями',
    'super.aiProvider': 'AI провайдер',
    'super.provider': 'Провайдер',
    'super.model': 'Модель',
    'super.baseUrl': 'Base URL',
    'super.apiKey': 'API ключ',
    'super.saveAiProvider': 'Сохранить AI провайдера',
    'super.aiProviderSaved': 'AI провайдер сохранен.',
    'super.aiProviderFailed': 'Не удалось сохранить AI провайдера.',
    'super.liveProviderRequirements': 'Для live-провайдеров нужны модель и API ключ.',
    'super.userPasswords': 'Пароли пользователей',
    'super.userPasswordsNote': 'Текущие пароли не отображаются. Выберите пользователя рабочей области и задайте новый временный пароль.',
    'super.newTemporaryPassword': 'Новый временный пароль',
    'super.confirmTemporaryPassword': 'Подтвердите временный пароль',
    'super.loadingUsers': 'Загрузка пользователей...',
    'super.noUsers': 'В этой рабочей области пользователи не найдены.',
    'super.resetPassword': 'Сбросить пароль',
    'super.resettingPassword': 'Сброс...',
    'super.selectUserFirst': 'Сначала выберите пользователя рабочей области.',
    'super.passwordMismatch': 'Пароли не совпадают.',
    'super.passwordTooShort': 'Пароль должен быть не короче 8 символов.',
    'super.passwordReset': 'Пароль обновлен',
    'super.passwordResetFailed': 'Не удалось обновить пароль.',
    'super.newWorkspace': 'Новая рабочая область',
    'super.activeWorkspaces': 'Активные рабочие области',
    'super.company': 'Компания',
    'super.subdomain': 'Субдомен',
    'super.adminContact': 'Контакт администратора',
    'super.modules': 'Модули',
    'super.manageModules': 'Настроить модули',
    'super.rename': 'Переименовать',
    'super.suspend': 'Остановить',
    'super.activate': 'Активировать',
    'super.launchWorkspace': 'Запустить новую рабочую область',
    'super.companyName': 'Название компании',
    'super.initialAdmin': 'Первый администратор',
    'super.emailAddress': 'Email адрес',
    'super.createWorkspace': 'Создать рабочую область',
    'super.creatingWorkspace': 'Создание...',
    'super.workspaceCreated': 'Рабочая область создана',
    'super.workspaceCreateFailed': 'Не удалось создать рабочую область. Проверьте субдомен и email.',
    'super.suspendConfirm': 'Остановить эту рабочую область?',
    'super.newWorkspaceName': 'Новое название рабочей области:',
    'super.workspaceModules': 'Модули рабочей области',
    'super.moduleSaveFailed': 'Не удалось сохранить модули рабочей области',
    'super.saveModules': 'Сохранить модули',
    'super.synergies': 'Синергии',
    'ai.title': 'Опишите, как работает ваш бизнес',
    'ai.subtitle': 'Опишите людей, записи, передачи между отделами, формы и отчеты простым языком. Система соберет предложение по CRM.',
    'ai.conversation': 'Диалог',
    'ai.emptyPrompt': 'Начните, например: "У нас ивент-агентство с аниматорами, заявками, программами и координаторами".',
    'ai.placeholder': 'Опишите бизнес-процесс...',
    'ai.send': 'Отправить',
    'ai.thinking': 'Думаю...',
    'ai.generate': 'Сгенерировать CRM blueprint',
    'ai.generating': 'Генерация...',
    'ai.blueprint': 'Blueprint бизнеса',
    'ai.profile': 'Профиль',
    'ai.departments': 'Отделы',
    'ai.roles': 'Роли',
    'ai.entities': 'Сущности',
    'ai.assumptions': 'Допущения',
    'ai.applied': 'Применено',
    'ai.applyProposal': 'Применить предложение',
    'ai.appliedArtifacts': 'Примененные объекты',
    'ai.history': 'История изменений AI',
    'ai.noHistory': 'История изменений пока пуста.',
    'ai.rollback': 'Откатить',
    'ai.you': 'Вы',
    'ai.failedStart': 'Не удалось запустить AI Архитектора.',
    'ai.failedSend': 'Не удалось отправить сообщение.',
    'ai.failedGenerate': 'Не удалось сгенерировать blueprint.',
    'ai.failedApply': 'Не удалось применить предложение.',
    'ai.failedRollback': 'Не удалось откатить изменение.',
    'home.welcomeBack': 'С возвращением',
    'home.subtitle': 'Заявки, формы, отчеты и действия рабочей области в одном месте.',
    'home.nextActions': 'Следующие действия',
    'home.fastRouting': 'Быстрый переход',
    'home.workspaceSections': 'Разделы рабочей области',
    'home.enabledShell': 'Доступные разделы',
    'home.ready': 'Готово',
    'home.soon': 'Скоро',
    'home.liveWorkflowData': 'Живые данные по заявкам',
    'home.installedTemplates': 'На основе установленных шаблонов',
    'home.readyForSetup': 'Готово к настройке',
    'home.weekEvents': 'События недели',
    'home.weekEventsSub': 'Заказы и репетиции из графика',
    'home.openSchedule': 'Открыть график',
    'home.noEvents': 'Свободно',
    'home.noAnimator': 'Аниматор не назначен',
    'market.general': 'Общая CRM',
    'market.functional': 'Функциональная CRM',
    'market.customers': 'Клиенты',
    'market.peopleDescription': 'Клиенты, компании, отделы и люди, с которыми работает команда.',
    'market.workDescription': 'Ежедневная работа: заявки, назначения, отделы, ответственные и текущие блокеры.',
    'market.moneyDescription': 'Финансовые процессы через формы, счета, долги и операционные записи.',
    'market.reportsDescription': 'Сохраненные отчеты и выгрузки для владельцев, менеджеров и администраторов.',
    'market.settingsDescription': 'Профиль, модули, AI Архитектор, пользователи, права и настройки рабочей области.',
    'market.createRequest': 'Создать заявку',
    'market.addCustomer': 'Добавить клиента',
    'market.openAiArchitect': 'Открыть AI Архитектора',
    'market.openSchedule': 'Открыть график',
    'market.needsAttention': 'Требует внимания',
    'market.recentWork': 'Последняя работа',
    'market.scheduleConflicts': 'Конфликты графика',
    'market.openRecords': 'Открыть записи',
    'market.openRequests': 'Открыть заявки',
    'market.openAssignedWork': 'Открыть назначенную работу',
    'market.departments': 'Отделы',
    'market.openForms': 'Открыть формы',
    'market.openReports': 'Открыть отчеты',
    'market.reportTypes': 'Типы отчетов',
    'market.openProfile': 'Открыть профиль',
    'market.adminPanel': 'Панель администратора',
    'market.crmModules': 'CRM-модули',
    'market.availableNow': 'Доступно сейчас',
    'market.destinations': 'переходов',
    'modules.title': 'Функциональные модули',
    'modules.coreModules': 'Функциональные модули',
    'modules.loading': 'Загрузка модулей...',
    'modules.open': 'Открыть модуль',
    'modules.noneEnabled': 'Для этой рабочей области не включены CRM-модули.',
    'modules.back': 'Назад к модулям',
    'modules.notFound': 'Модуль не найден',
    'modules.disabled': 'Этот модуль отключен для текущей рабочей области.',
    'modules.starterTemplates': 'стартовых шаблонов',
    'modules.starterKit': 'Стартовый комплект',
    'modules.templatesInstalled': 'шаблонов установлено',
    'modules.installTemplates': 'Установить шаблоны в эту рабочую область',
    'modules.installing': 'Установка...',
    'modules.installed': 'Установлено',
    'modules.installStarterKit': 'Установить стартовый комплект',
    'modules.installFailed': 'Не удалось установить стартовый комплект.',
    'modules.forms': 'формы',
    'modules.reports': 'отчеты',
    'modules.capabilities': 'Возможности',
    'modules.pluginTemplates': 'Шаблоны модуля',
    'modules.templatesConnected': 'стартовых шаблонов подключено к этому модулю',
    'modules.noTemplates': 'Для этого модуля пока нет опубликованных шаблонов.',
    'modules.connectedCore': 'Связанные базовые модули',
    'modules.managedTitle': 'Модули управляются в Суперадмин',
    'modules.managedDescription': 'Подключайте и отключайте базовые CRM-модули в настройках рабочей области. Отдельная установка стартового комплекта здесь больше не используется.',
    'modules.openSuperadmin': 'Открыть Суперадмин',
    'dashboard.openRequests': 'Открытые заявки',
    'dashboard.viewRequests': 'Посмотреть заявки',
    'dashboard.newRequest': '+ Новая заявка',
    'dashboard.quickRequest': 'Быстрая заявка',
    'dashboard.manageTemplates': 'Управлять шаблонами',
    'dashboard.close': 'Закрыть',
    'dashboard.cannotCreate': 'Ваша роль не может создавать заявки из шаблонов.',
    'dashboard.noTemplates': 'Шаблонов пока нет. Сначала создайте шаблон в формах.',
    'dashboard.requestSubmitted': 'Заявка отправлена',
    'dashboard.submitFailed': 'Не удалось отправить заявку',
    'forms.noTemplates': 'Шаблонов пока нет.',
    'requests.noTemplates': 'Шаблонов пока нет.',
    'template.registry': 'Реестр',
    'template.workflow': 'Процесс',
    'template.form': 'Динамическая форма',
    'template.report': 'Отчет',
  },
  en: {
    'common.loading': 'Loading...',
    'common.cancel': 'Cancel',
    'common.save': 'Save',
    'common.edit': 'Edit',
    'common.delete': 'Delete',
    'common.actions': 'Actions',
    'common.active': 'Active',
    'common.inactive': 'Inactive',
    'common.suspended': 'Suspended',
    'common.backHome': 'Back to Home',
    'common.language': 'Language',
    'common.russian': 'Russian',
    'common.english': 'English',
    'common.workspace': 'Workspace',
    'common.workspaces': 'Workspaces',
    'common.user': 'User',
    'common.users': 'Users',
    'common.name': 'Name',
    'common.email': 'Email',
    'common.password': 'Password',
    'common.role': 'Role',
    'common.department': 'Department',
    'common.status': 'Status',
    'common.description': 'Description',
    'login.heroTitle': 'Operations workspace for events, teams, and client work.',
    'login.heroCopy': 'Track requests, forms, reports, files, and workspace configuration from one dense production surface.',
    'login.signIn': 'Sign in',
    'login.useAccount': 'Use your workspace account.',
    'login.email': 'Email',
    'login.password': 'Password',
    'login.signingIn': 'Signing in...',
    'login.invalidCredentials': 'Invalid credentials',
    'nav.home': 'Home',
    'nav.dashboard': 'Dashboard',
    'nav.people': 'Clients',
    'nav.work': 'Work',
    'nav.money': 'Money',
    'nav.schedule': 'Schedule',
    'nav.employeeEvaluations': 'Employee evaluations',
    'nav.reports': 'Reports',
    'nav.settings': 'Settings',
    'nav.system': 'System',
    'nav.workspace': 'Workspace',
    'nav.aiArchitect': 'AI Architect',
    'nav.admin': 'Admin',
    'nav.superadmin': 'Superadmin',
    'nav.searchWorkspace': 'Search workspace',
    'nav.assigned': 'Assigned',
    'nav.profile': 'Profile',
    'nav.newPending': 'new / pending',
    'nav.requestHistory': 'Request history',
    'nav.newTemplate': 'New template',
    'profile.title': 'My Profile',
    'profile.role': 'Role',
    'profile.workspaceInfo': 'Workspace',
    'profile.loadingWorkspace': 'Loading workspace info...',
    'profile.department': 'Department',
    'profile.fullName': 'Full Name',
    'profile.accountStatus': 'Account Status',
    'profile.editProfile': 'Edit Profile',
    'profile.saveChanges': 'Save Changes',
    'profile.updated': 'Profile updated successfully',
    'profile.updateFailed': 'Failed to update profile',
    'profile.logout': 'Logout from account',
    'admin.title': 'User Management',
    'admin.selectWorkspace': 'Select Workspace:',
    'admin.createUser': 'Create User',
    'admin.createNewUser': 'Create New User',
    'admin.noUsers': 'No users in this workspace',
    'admin.fullName': 'Full Name:',
    'admin.role': 'Role:',
    'admin.accessProfile': 'Access profile',
    'admin.accessProfiles': 'Access profiles',
    'admin.accessProfileName': 'Profile name',
    'admin.baseRole': 'Base role',
    'admin.tabVisibility': 'Tab visibility',
    'admin.fieldVisibility': 'Form field visibility',
    'admin.noFormFields': 'Fields will appear here after form templates are created.',
    'admin.noAccessProfile': 'No separate profile',
    'admin.createAccessProfile': 'Create access profile',
    'admin.saveAccessProfile': 'Save access profile',
    'admin.accessProfileCreated': 'Access profile created',
    'admin.accessProfileUpdated': 'Access profile updated',
    'admin.accessProfileSaveFailed': 'Failed to save access profile',
    'admin.accessProfileUpdateFailed': 'Failed to update user access profile',
    'admin.deleteAccessProfileConfirm': 'Delete this access profile?',
    'admin.roleNameRequired': 'Enter an access profile name',
    'admin.selectWorkspacePlaceholder': '-- Select Workspace --',
    'admin.selectDepartmentPlaceholder': '-- Select Department --',
    'admin.unassigned': '-- Unassigned --',
    'admin.deactivate': 'Deactivate',
    'admin.reactivate': 'Reactivate',
    'admin.userCreated': 'User created successfully',
    'admin.createFailed': 'Failed to create user',
    'admin.roleUpdated': 'User role updated',
    'admin.roleUpdateFailed': 'Failed to update role',
    'admin.selfRoleBlocked': 'You cannot change your own role. Ask another admin to do this.',
    'admin.departmentUpdateFailed': 'Failed to update department',
    'admin.statusUpdateFailed': 'Failed to update user status',
    'admin.departments': 'Departments',
    'admin.departmentName': 'Department name',
    'admin.descriptionOptional': 'Description (optional)',
    'admin.add': 'Add',
    'admin.noDepartments': 'No departments found',
    'admin.deleteDepartmentConfirm': 'Delete this department?',
    'super.title': 'Superadmin Control Center',
    'super.subtitle': 'System-wide workspace management',
    'super.aiProvider': 'AI Provider',
    'super.provider': 'Provider',
    'super.model': 'Model',
    'super.baseUrl': 'Base URL',
    'super.apiKey': 'API key',
    'super.saveAiProvider': 'Save AI Provider',
    'super.aiProviderSaved': 'AI provider saved.',
    'super.aiProviderFailed': 'Failed to save AI provider.',
    'super.liveProviderRequirements': 'Model and API key are required for live providers.',
    'super.userPasswords': 'User Passwords',
    'super.userPasswordsNote': 'Current passwords are never shown. Select a workspace user and set a new temporary password.',
    'super.newTemporaryPassword': 'New temporary password',
    'super.confirmTemporaryPassword': 'Confirm temporary password',
    'super.loadingUsers': 'Loading users...',
    'super.noUsers': 'No users found for this workspace.',
    'super.resetPassword': 'Reset User Password',
    'super.resettingPassword': 'Resetting...',
    'super.selectUserFirst': 'Select a workspace user first.',
    'super.passwordMismatch': 'New passwords do not match.',
    'super.passwordTooShort': 'New password must be at least 8 characters.',
    'super.passwordReset': 'Password reset',
    'super.passwordResetFailed': 'Failed to reset password.',
    'super.newWorkspace': 'New Workspace',
    'super.activeWorkspaces': 'Active Workspaces',
    'super.company': 'Company',
    'super.subdomain': 'Subdomain',
    'super.adminContact': 'Admin Contact',
    'super.modules': 'Modules',
    'super.manageModules': 'Manage Modules',
    'super.rename': 'Rename',
    'super.suspend': 'Suspend',
    'super.activate': 'Activate',
    'super.launchWorkspace': 'Launch New Workspace',
    'super.companyName': 'Company Name',
    'super.initialAdmin': 'Initial Admin User',
    'super.emailAddress': 'Email Address',
    'super.createWorkspace': 'Create Workspace',
    'super.creatingWorkspace': 'Creating...',
    'super.workspaceCreated': 'Workspace created',
    'super.workspaceCreateFailed': 'Failed to create workspace. Check if subdomain or email exists.',
    'super.suspendConfirm': 'Suspend this workspace?',
    'super.newWorkspaceName': 'New workspace name:',
    'super.workspaceModules': 'Workspace Modules',
    'super.moduleSaveFailed': 'Failed to save workspace modules',
    'super.saveModules': 'Save Modules',
    'super.synergies': 'Synergies',
    'ai.title': 'Describe how your business works',
    'ai.subtitle': 'Explain your people, records, handoffs, forms, and reports in plain language. The system will turn that into a proposed CRM blueprint.',
    'ai.conversation': 'Conversation',
    'ai.emptyPrompt': 'Start with something like: "We run an event CRM with clients, orders, assignments, schedule, payments, and reports."',
    'ai.placeholder': 'Explain your business process...',
    'ai.send': 'Send',
    'ai.thinking': 'Thinking...',
    'ai.generate': 'Generate CRM blueprint',
    'ai.generating': 'Generating...',
    'ai.blueprint': 'Business blueprint',
    'ai.profile': 'Profile',
    'ai.departments': 'Departments',
    'ai.roles': 'Roles',
    'ai.entities': 'Entities',
    'ai.assumptions': 'Assumptions',
    'ai.applied': 'Applied',
    'ai.applyProposal': 'Apply proposal',
    'ai.appliedArtifacts': 'Applied artifacts',
    'ai.history': 'AI change history',
    'ai.noHistory': 'No AI changes yet.',
    'ai.rollback': 'Roll back',
    'ai.you': 'You',
    'ai.failedStart': 'Failed to start AI Architect.',
    'ai.failedSend': 'Failed to send message.',
    'ai.failedGenerate': 'Failed to generate blueprint.',
    'ai.failedApply': 'Failed to apply proposal.',
    'ai.failedRollback': 'Failed to roll back change.',
    'home.welcomeBack': 'Welcome back',
    'home.subtitle': 'Requests, forms, reports, and workspace actions in one place.',
    'home.nextActions': 'Next best actions',
    'home.fastRouting': 'Fast routing',
    'home.workspaceSections': 'Workspace sections',
    'home.enabledShell': 'Enabled shell',
    'home.ready': 'Ready',
    'home.soon': 'Soon',
    'home.liveWorkflowData': 'Live workflow data',
    'home.installedTemplates': 'Driven by installed templates',
    'home.readyForSetup': 'Ready for setup',
    'home.weekEvents': 'Week events',
    'home.weekEventsSub': 'Orders and rehearsals from the schedule',
    'home.openSchedule': 'Open schedule',
    'home.noEvents': 'Free',
    'home.noAnimator': 'Animator not assigned',
    'market.general': 'General CRM',
    'market.functional': 'Functional CRM',
    'market.customers': 'Customers',
    'market.peopleDescription': 'Customers, companies, departments, and the people your event team works with.',
    'market.workDescription': 'Daily execution: requests, assignments, departments, ownership, and current blockers.',
    'market.moneyDescription': 'Form-driven financial workflows, invoices, debts, and money-facing operating records.',
    'market.reportsDescription': 'Stored reports and generated exports for owners, managers, and administrators.',
    'market.settingsDescription': 'Profile, modules, AI Architect, users, permissions, and workspace configuration.',
    'market.createRequest': 'Create request',
    'market.addCustomer': 'Add customer',
    'market.openAiArchitect': 'Open AI Architect',
    'market.openSchedule': 'Open schedule',
    'market.needsAttention': 'Needs attention',
    'market.recentWork': 'Recent work',
    'market.scheduleConflicts': 'Schedule conflicts',
    'market.openRecords': 'Open records',
    'market.openRequests': 'Open requests',
    'market.openAssignedWork': 'Open assigned work',
    'market.departments': 'Departments',
    'market.openForms': 'Open forms',
    'market.openReports': 'Open reports',
    'market.reportTypes': 'Report types',
    'market.openProfile': 'Open profile',
    'market.adminPanel': 'Admin panel',
    'market.crmModules': 'CRM modules',
    'market.availableNow': 'Available now',
    'market.destinations': 'destinations',
    'modules.title': 'Functional Modules',
    'modules.coreModules': 'Functional Modules',
    'modules.loading': 'Loading modules...',
    'modules.open': 'Open Module',
    'modules.noneEnabled': 'No CRM modules are enabled for this workspace.',
    'modules.back': 'Back to Modules',
    'modules.notFound': 'Module Not Found',
    'modules.disabled': 'This module is disabled for the current workspace.',
    'modules.starterTemplates': 'starter templates',
    'modules.starterKit': 'Starter Kit',
    'modules.templatesInstalled': 'templates installed',
    'modules.installTemplates': 'Install templates into this workspace',
    'modules.installing': 'Installing...',
    'modules.installed': 'Installed',
    'modules.installStarterKit': 'Install Starter Kit',
    'modules.installFailed': 'Failed to install starter kit.',
    'modules.forms': 'forms',
    'modules.reports': 'reports',
    'modules.capabilities': 'Capabilities',
    'modules.pluginTemplates': 'Plugin Templates',
    'modules.templatesConnected': 'starter templates connected to this module',
    'modules.noTemplates': 'No templates are published for this module yet.',
    'modules.connectedCore': 'Connected Core Modules',
    'modules.managedTitle': 'Modules are managed in Superadmin',
    'modules.managedDescription': 'Connect and disconnect core CRM modules from workspace settings. Starter-kit installs are no longer managed from this page.',
    'modules.openSuperadmin': 'Open Superadmin',
    'dashboard.openRequests': 'Open requests',
    'dashboard.viewRequests': 'View Requests',
    'dashboard.newRequest': '+ New Request',
    'dashboard.quickRequest': 'Quick Request',
    'dashboard.manageTemplates': 'Manage Templates',
    'dashboard.close': 'Close',
    'dashboard.cannotCreate': 'Your role cannot create requests from templates.',
    'dashboard.noTemplates': 'No templates available. Create one in Forms first.',
    'dashboard.requestSubmitted': 'Request submitted successfully',
    'dashboard.submitFailed': 'Failed to submit request',
    'forms.noTemplates': 'No templates yet.',
    'requests.noTemplates': 'No templates available yet.',
    'template.registry': 'Registry',
    'template.workflow': 'Workflow',
    'template.form': 'Dynamic Form',
    'template.report': 'Report',
  },
}

const readInitialLanguage = (): AppLanguage => {
  if (typeof window === 'undefined') return 'ru'
  return normalizeLanguage(window.localStorage.getItem('crm_language'))
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<AppLanguage>(readInitialLanguage)

  const setLanguage = useCallback((nextLanguage: AppLanguage) => {
    setLanguageState(nextLanguage)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('crm_language', nextLanguage)
    }
  }, [])

  useEffect(() => {
    document.documentElement.lang = language
  }, [language])

  const t = useCallback((key: TranslationKey) => {
    return translations[language][key] || translations.ru[key] || key
  }, [language])

  const value = useMemo(() => ({ language, setLanguage, t }), [language, setLanguage, t])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}
