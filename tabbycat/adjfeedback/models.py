from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from django.utils.html import escape
from django.utils.translation import gettext, gettext_lazy as _
from django_better_admin_arrayfield.models.fields import ArrayField

from adjallocation.models import DebateAdjudicator
from results.models import Submission


class AdjudicatorBaseScoreHistory(models.Model):
    adjudicator = models.ForeignKey('participants.Adjudicator', models.CASCADE,
        verbose_name=_("adjudicator"))
    # cascade to avoid ambiguity, null round indicates beginning of tournament
    round = models.ForeignKey('tournaments.Round', models.CASCADE, blank=True, null=True,
        verbose_name=_("round"))
    score = models.FloatField(verbose_name=_("score"))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("timestamp"))

    class Meta:
        verbose_name = _("adjudicator base score history")
        verbose_name_plural = _("adjudicator base score histories")

    def __str__(self):
        return "{.name:s} ({:.1f}) in {!s}".format(self.adjudicator, self.score, self.round)


class AdjudicatorFeedbackAnswer(models.Model):
    question = models.ForeignKey('AdjudicatorFeedbackQuestion', models.CASCADE,
        verbose_name=_("question"))
    feedback = models.ForeignKey('AdjudicatorFeedback', models.CASCADE,
        verbose_name=_("feedback"))

    class Meta:
        abstract = True
        unique_together = [('question', 'feedback')]


class BooleanAnswerMixin:
    ANSWER_TYPE = bool

    # Note: by convention, if no answer is chosen for a boolean answer, an
    # instance of this object should not be created. This way, there is no need
    # for a NullBooleanField.
    answer = models.BooleanField(verbose_name=_("answer"))


class IntegerAnswerMixin:
    ANSWER_TYPE = int
    answer = models.IntegerField(verbose_name=_("answer"))


class FloatAnswerMixin:
    ANSWER_TYPE = float
    answer = models.FloatField(verbose_name=_("answer"))


class StringAnswerMixin:
    ANSWER_TYPE = str
    answer = models.TextField(verbose_name=_("answer"))


class ArrayAnswerMixin:
    ANSWER_TYPE = list
    answer = ArrayField(base_field=models.TextField(), verbose_name=_("answer"))


class AdjudicatorFeedbackBooleanAnswer(BooleanAnswerMixin, AdjudicatorFeedbackAnswer):

    class Meta(AdjudicatorFeedbackAnswer.Meta):
        verbose_name = _("adjudicator feedback boolean answer")
        verbose_name_plural = _("adjudicator feedback boolean answers")


class AdjudicatorFeedbackIntegerAnswer(IntegerAnswerMixin, AdjudicatorFeedbackAnswer):

    class Meta(AdjudicatorFeedbackAnswer.Meta):
        verbose_name = _("adjudicator feedback integer answer")
        verbose_name_plural = _("adjudicator feedback integer answers")


class AdjudicatorFeedbackFloatAnswer(FloatAnswerMixin, AdjudicatorFeedbackAnswer):

    class Meta(AdjudicatorFeedbackAnswer.Meta):
        verbose_name = _("adjudicator feedback float answer")
        verbose_name_plural = _("adjudicator feedback float answers")


class AdjudicatorFeedbackStringAnswer(StringAnswerMixin, AdjudicatorFeedbackAnswer):

    class Meta(AdjudicatorFeedbackAnswer.Meta):
        verbose_name = _("adjudicator feedback string answer")
        verbose_name_plural = _("adjudicator feedback string answers")


class AdjudicatorFeedbackManyAnswer(ArrayAnswerMixin, AdjudicatorFeedbackAnswer):

    class Meta(AdjudicatorFeedbackAnswer.Meta):
        verbose_name = _("adjudicator feedback multiple select answer")
        verbose_name_plural = _("adjudicator feedback multiple select answers")


class AnswerType(models.TextChoices):
    BOOLEAN_CHECKBOX = 'bc', _("checkbox")
    BOOLEAN_SELECT = 'bs', _("yes/no (dropdown)")
    INTEGER_TEXTBOX = 'i', _("integer (textbox)")
    INTEGER_SCALE = 'is', _("integer scale")
    FLOAT = 'f', _("float")
    TEXT = 't', _("text")
    LONGTEXT = 'tl', _("long text")
    SINGLE_SELECT = 'ss', _("select one")
    MULTIPLE_SELECT = 'ms', _("select multiple")


class BaseQuestion(models.Model):
    tournament = models.ForeignKey('tournaments.Tournament', models.CASCADE,
        verbose_name=_("tournament"))
    seq = models.IntegerField(help_text="The order in which questions are displayed",
        verbose_name=_("sequence number"))
    text = models.CharField(max_length=255,
        verbose_name=_("text"),
        help_text=_("The question displayed to participants, e.g., \"Did you agree with the decision?\""))
    name = models.CharField(max_length=30,
        verbose_name=_("name"),
        help_text=_("A short name for the question, e.g., \"Agree with decision\""))

    answer_type = models.CharField(max_length=2, choices=AnswerType.choices,
        verbose_name=_("answer type"))
    required = models.BooleanField(default=True,
        verbose_name=_("required"),
        help_text=_("Whether participants are required to fill out this field"))
    min_value = models.FloatField(blank=True, null=True,
        verbose_name=_("minimum value"),
        help_text=_("Minimum allowed value for numeric fields (ignored for text or boolean fields)"))
    max_value = models.FloatField(blank=True, null=True,
        verbose_name=_("maximum value"),
        help_text=_("Maximum allowed value for numeric fields (ignored for text or boolean fields)"))

    choices = ArrayField(
        base_field=models.TextField(),
        blank=True,
        verbose_name=_("choices"),
        help_text=_("Permissible choices for select one/multiple fields (ignored for other fields)"),
        default=list)

    class Meta:
        abstract = True


class AdjudicatorFeedbackQuestion(BaseQuestion):
    # When adding or changing an answer type, here are the other places you need
    # to edit:
    #   - forms.py : BaseFeedbackForm._make_question_field()
    #   - importer/importers/anorak.py : AnorakTournamentDataImporter.FEEDBACK_ANSWER_TYPES

    ANSWER_CLASSES = {
        AnswerType.BOOLEAN_CHECKBOX: AdjudicatorFeedbackBooleanAnswer,
        AnswerType.BOOLEAN_SELECT: AdjudicatorFeedbackBooleanAnswer,
        AnswerType.INTEGER_TEXTBOX: AdjudicatorFeedbackIntegerAnswer,
        AnswerType.INTEGER_SCALE: AdjudicatorFeedbackIntegerAnswer,
        AnswerType.FLOAT: AdjudicatorFeedbackFloatAnswer,
        AnswerType.TEXT: AdjudicatorFeedbackStringAnswer,
        AnswerType.LONGTEXT: AdjudicatorFeedbackStringAnswer,
        AnswerType.SINGLE_SELECT: AdjudicatorFeedbackStringAnswer,
        AnswerType.MULTIPLE_SELECT: AdjudicatorFeedbackManyAnswer,
    }
    ANSWER_CLASSES_REVERSE = {
        AdjudicatorFeedbackStringAnswer: [AnswerType.TEXT,
                                          AnswerType.LONGTEXT,
                                          AnswerType.SINGLE_SELECT],
        AdjudicatorFeedbackManyAnswer: [AnswerType.MULTIPLE_SELECT],
        AdjudicatorFeedbackIntegerAnswer:
        [AnswerType.INTEGER_SCALE, AnswerType.INTEGER_TEXTBOX],
        AdjudicatorFeedbackFloatAnswer: [AnswerType.FLOAT],
        AdjudicatorFeedbackBooleanAnswer:
        [AnswerType.BOOLEAN_SELECT, AnswerType.BOOLEAN_CHECKBOX],
    }
    NUMERICAL_ANSWER_TYPES = [AnswerType.INTEGER_TEXTBOX, AnswerType.INTEGER_SCALE, AnswerType.FLOAT]

    reference = models.SlugField(
        verbose_name=_("reference"),
        help_text=_("Code-compatible reference, e.g., \"agree_with_decision\""))

    from_adj = models.BooleanField(
        verbose_name=_("from adjudicator"),
        help_text=_("Adjudicators should be asked this question (about other adjudicators)"))
    from_team = models.BooleanField(
        verbose_name=_("from team"),
        help_text=_("Teams should be asked this question"))

    class Meta:
        unique_together = [('tournament', 'reference'), ('tournament', 'seq')]
        verbose_name = _("adjudicator feedback question")
        verbose_name_plural = _("adjudicator feedback questions")

    def __str__(self):
        return self.reference

    @property
    def answer_set(self):
        return self.answer_type_class.objects.filter(question=self)

    @property
    def answer_type_class(self):
        return self.ANSWER_CLASSES[self.answer_type]

    @property
    def choices_for_field(self):
        return tuple((x, x) for x in self.choices)

    @property
    def choices_for_number_scale(self):
        return self.construct_number_scale(self.min_value, self.max_value)

    def construct_number_scale(self, min_value, max_value):
        """Used to build up a semi-intelligent range of options for numeric scales.
        Shifted here rather than the class so that it can be more easily used to
        construct the default values for printed forms."""
        step = max((int(max_value) - int(min_value)) / 10, 1)
        options = list(range(int(min_value), int(max_value + 1), int(step)))
        return options

    def serialize(self):
        question = {
            'text': escape(self.text),
            'seq': self.seq,
            'type': self.answer_type,
            'required': self.answer_type,
            'from_team': self.from_team,
            'from_adj': self.from_adj,
        }
        if self.choices:
            question['choice_options'] = [escape(c) for c in self.choices]
        elif self.min_value is not None and self.max_value is not None:
            question['choice_options'] = self.choices_for_number_scale
        return question


class AdjudicatorFeedback(Submission):
    adjudicator = models.ForeignKey('participants.Adjudicator', models.CASCADE, db_index=True,
        verbose_name=_("adjudicator"))
    score = models.FloatField(verbose_name=_("score"))

    # cascade to avoid double-null sources, each feedback must have exactly one source
    source_adjudicator = models.ForeignKey('adjallocation.DebateAdjudicator', models.CASCADE, blank=True, null=True,
        verbose_name=_("source adjudicator"))
    source_team = models.ForeignKey('draw.DebateTeam', models.CASCADE, blank=True, null=True,
        verbose_name=_("source team"))

    ignored = models.BooleanField(default=False,
        verbose_name=_("ignored"),
        help_text=_("Whether the feedback should affect the adjudicator's score"))

    class Meta:
        unique_together = [('adjudicator', 'source_adjudicator', 'source_team', 'version')]
        verbose_name = _("adjudicator feedback")
        verbose_name_plural = _("adjudicator feedbacks")

    def __str__(self):
        return "Feedback from {source} on {adj} submitted at {time} (version {version})".format(
            source=self.source,
            adj=self.adjudicator.name,
            version=self.version,
            time=('<unknown>' if self.timestamp is None else str(
                self.timestamp.isoformat())))

    def _unique_unconfirm_args(self):
        kwargs = super()._unique_unconfirm_args()
        if self.source_team is not None and self.source_team.debate.round.tournament.pref('feedback_from_teams') == 'orallist':
            kwargs.pop('adjudicator')
        return kwargs

    @cached_property
    def source(self):
        if self.source_adjudicator:
            return self.source_adjudicator.adjudicator.name
        if self.source_team:
            return self.source_team.team.short_name

    @cached_property
    def debate(self):
        if self.source_adjudicator:
            return self.source_adjudicator.debate
        if self.source_team:
            return self.source_team.debate

    @cached_property
    def debate_adjudicator(self):
        if not hasattr(self, '_debateadj'):
            try:
                self._debateadj = self.adjudicator.debateadjudicator_set.get(
                    debate=self.debate)
            except DebateAdjudicator.DoesNotExist:
                self._debateadj = None
        return self._debateadj

    @property
    def round(self):
        return self.debate.round

    @cached_property
    def feedback_weight(self):
        if self.round:
            return self.round.feedback_weight
        return 1

    def get_answers(self):
        return [
            {'question': q.question, 'answer': q.answer}
            for typ in AdjudicatorFeedbackQuestion.ANSWER_CLASSES_REVERSE.keys()
            for q in getattr(self, typ.__name__.lower() + '_set').all()
        ]

    def clean(self):
        if not (self.source_adjudicator or self.source_team):
            raise ValidationError(
                gettext("Either the source adjudicator or source team wasn't specified."))
        if self.source_adjudicator and self.source_team:
            raise ValidationError(
                gettext("There was both a source adjudicator and a source team."))
        if not self.adjudicator:
            raise ValidationError(gettext("There is no adjudicator specified as the target for this feedback. Perhaps they were deleted?"))
        if self.adjudicator not in self.debate.adjudicators:
            raise ValidationError(gettext("Adjudicator did not see this debate."))
        return super(AdjudicatorFeedback, self).clean()
